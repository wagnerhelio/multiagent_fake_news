import logging
import queue
import time
from typing import Dict, List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SchedulerAgent:
    def __init__(self):
        # Queues for different content types, ordered by priority (higher overall_priority means higher priority)
        self.content_queues: Dict[str, queue.PriorityQueue] = {
            "Política": queue.PriorityQueue(),
            "Saúde": queue.PriorityQueue(),
            "Economia": queue.PriorityQueue(),
            "Mundo": queue.PriorityQueue(),
            "Esportes": queue.PriorityQueue(),
            "Geral": queue.PriorityQueue(),
            "unknown": queue.PriorityQueue() # For uncategorized content
        }
        self.checking_units_capacity = 5 # Max concurrent checks
        self.active_checks: List[Dict] = []
        self.preempted_content: Dict[str, Dict] = {}
        logging.info("SchedulerAgent initialized.")

    def add_content_to_queue(self, content_metadata: Dict):
        """
        Adds content to the appropriate queue based on its category and priority.
        """
        category = content_metadata.get('category', 'unknown')
        overall_priority = content_metadata.get('overall_priority', 0)

        # PriorityQueue stores (priority, item). Lower number means higher priority.
        # We want higher overall_priority to mean higher priority, so we negate it.
        # Add a unique sequence number to handle items with the same priority (tie-breaker)
        # This prevents TypeError when comparing content_metadata dictionaries
        self.counter = getattr(self, 'counter', 0) + 1
        priority_tuple = (-overall_priority, self.counter, content_metadata)

        self.content_queues[category].put(priority_tuple)
        logging.info(f"Content {content_metadata.get('id')} added to {category} queue with priority {overall_priority}.")

    def _get_highest_priority_content(self) -> Dict | None:
        """
        Retrieves the highest priority content from all queues.
        """
        highest_priority_item = None
        highest_priority_category = None

        for category, q in self.content_queues.items():
            if not q.empty():
                # Peek at the item without removing it
                current_item = q.queue[0] # PriorityQueue's internal list
                if highest_priority_item is None or current_item[0] < highest_priority_item[0] or \
                   (current_item[0] == highest_priority_item[0] and current_item[1] < highest_priority_item[1]):
                    highest_priority_item = current_item
                    highest_priority_category = category
        
        if highest_priority_item: # If an item was found, remove it from its queue
            self.content_queues[highest_priority_category].get() # Remove the item
            return highest_priority_item[2] # Return the content_metadata
        return None

    def _check_for_preemption(self, new_content: Dict) -> bool:
        """
        Checks if any active checks should be preempted by the new, higher priority content.
        Returns True if preemption occurred, False otherwise.
        """
        new_content_priority = new_content.get('overall_priority', 0)
        preempted_count = 0
        items_to_remove = []

        for i, active_check in enumerate(self.active_checks):
            active_check_priority = active_check.get('overall_priority', 0)
            # Define preemption criteria: new content is significantly higher priority
            # For example, if new content priority is 2 points higher than active content
            if new_content_priority > active_check_priority + 2: # Example threshold
                logging.warning(f"Preempting active check {active_check.get('id')} (priority {active_check_priority}) for new content {new_content.get('id')} (priority {new_content_priority}).")
                active_check['status'] = 'preempted'
                self.preempted_content[active_check['id']] = active_check
                self.add_content_to_queue(active_check) # Put it back in queue
                items_to_remove.append(i)
                preempted_count += 1
        
        # Remove preempted items from active_checks (iterate backwards to avoid index issues)
        for i in sorted(items_to_remove, reverse=True):
            del self.active_checks[i]

        return preempted_count > 0

    def schedule_content(self) -> List[Dict]:
        """
        Schedules content for checking, applying preemption if necessary.
        Returns a list of content items ready to be dispatched to checking units.
        """
        dispatch_list = []

        # First, check if there's any new high-priority content that requires preemption
        # This part is tricky with a simple PriorityQueue as it doesn't allow peeking across all queues easily
        # For a real system, a global priority queue or a more sophisticated queue management would be needed.
        # For this prototype, we'll simplify: if capacity is full, we check for preemption when a new item arrives.

        # Try to fill available capacity
        while len(self.active_checks) < self.checking_units_capacity:
            next_content = self._get_highest_priority_content()
            if next_content:
                # Check for preemption only if capacity is full and a new high-priority item arrives
                if len(self.active_checks) == self.checking_units_capacity and self._check_for_preemption(next_content):
                    # If preemption happened, some slots might have opened, try to schedule again
                    continue 
                
                next_content['status'] = 'in_analysis'
                next_content['timestamp_scheduled'] = logging.Formatter().formatTime(logging.LogRecord(None, None, None, None, None, None, None), '%Y-%m-%d %H:%M:%S')
                self.active_checks.append(next_content)
                dispatch_list.append(next_content)
                logging.info(f"Content {next_content.get('id')} scheduled for analysis.")
            else:
                break # No more content in queues
        
        return dispatch_list

    def complete_check(self, content_id: str, result_metadata: Dict):
        """
        Marks a content item as completed and removes it from active checks.
        """
        self.active_checks = [item for item in self.active_checks if item['id'] != content_id]
        logging.info(f"Content {content_id} check completed and removed from active checks.")

    def get_queue_status(self) -> Dict:
        """
        Returns the current status of all queues and active checks.
        """
        status = {
            "queue_sizes": {category: q.qsize() for category, q in self.content_queues.items()},
            "active_checks_count": len(self.active_checks),
            "active_checks_ids": [item['id'] for item in self.active_checks],
            "preempted_content_count": len(self.preempted_content),
            "preempted_content_ids": list(self.preempted_content.keys())
        }
        return status

if __name__ == '__main__':
    # Simulate the full pipeline for testing the scheduler
    from ingestion_agent import IngestionAgent
    from categorization_agent import CategorizationAgent
    from priority_agent import PriorityAgent
    import os
    import shutil

    # Setup temporary directory for ingested content
    temp_output_dir = "./temp_ingested_content_for_scheduler_test"
    if os.path.exists(temp_output_dir):
        shutil.rmtree(temp_output_dir)
    os.makedirs(temp_output_dir)

    ingestion_agent = IngestionAgent(output_dir=temp_output_dir)
    categorization_agent = CategorizationAgent()
    priority_agent = PriorityAgent()
    scheduler_agent = SchedulerAgent()

    # --- Simulate content ingestion and processing ---
    contents_to_process = [
        {'type': 'text', 'source': 'G1', 'raw_content': 'Notícia de política de baixa urgência.'},
        {'type': 'text', 'source': 'Folha', 'raw_content': 'Urgente: Nova crise econômica global.'},
        {'type': 'text', 'source': 'CNN', 'raw_content': 'Descoberta médica importante na saúde.'},
        {'type': 'text', 'source': 'ESPN', 'raw_content': 'Resultado de jogo de futebol.'},
        {'type': 'text', 'source': 'Blog', 'raw_content': 'Fato curioso sobre o mundo.'},
        {'type': 'text', 'source': 'Local News', 'raw_content': 'Evento comunitário.'},
        {'type': 'text', 'source': 'Alert News', 'raw_content': 'Alerta de segurança pública de alta gravidade.'},
    ]

    processed_contents = []
    for i, content_data in enumerate(contents_to_process):
        ingested = ingestion_agent.ingest_content(content_data)
        categorized = categorization_agent.categorize_content(ingested)
        prioritized = priority_agent.assign_priority(categorized)
        processed_contents.append(prioritized)
        scheduler_agent.add_content_to_queue(prioritized)
        time.sleep(0.1) # Simulate some delay

    logging.info("\n--- Initial Queue Status ---")
    print(scheduler_agent.get_queue_status())

    # --- Simulate scheduling and preemption ---
    logging.info("\n--- Scheduling first batch ---")
    dispatched_1 = scheduler_agent.schedule_content()
    print("Dispatched 1:", [c['id'] for c in dispatched_1])
    print(scheduler_agent.get_queue_status())

    logging.info("\n--- Scheduling second batch (should fill capacity) ---")
    dispatched_2 = scheduler_agent.schedule_content()
    print("Dispatched 2:", [c['id'] for c in dispatched_2])
    print(scheduler_agent.get_queue_status())

    logging.info("\n--- Simulate a high priority item arriving and preemption ---")
    high_priority_content_data = {
        'type': 'text',
        'source': 'Emergency Broadcast',
        'raw_content': 'URGENTE: Desastre natural iminente!'
    }
    ingested_hp = ingestion_agent.ingest_content(high_priority_content_data)
    categorized_hp = categorization_agent.categorize_content(ingested_hp)
    # Manually set very high priority for testing preemption
    prioritized_hp = {**categorized_hp, 'gut_gravidade': 5, 'gut_urgencia': 5, 'gut_tendencia': 5, 'overall_priority': 15}
    scheduler_agent.add_content_to_queue(prioritized_hp)

    logging.info("\n--- Scheduling after high priority arrival (expect preemption) ---")
    dispatched_3 = scheduler_agent.schedule_content()
    print("Dispatched 3:", [c['id'] for c in dispatched_3])
    print(scheduler_agent.get_queue_status())

    # Simulate completing some checks
    if dispatched_1:
        scheduler_agent.complete_check(dispatched_1[0]['id'], {'result': 'fake'}) # Simulate result
    logging.info("\n--- After completing one check ---")
    print(scheduler_agent.get_queue_status())

    # Clean up temporary files
    if os.path.exists(temp_output_dir):
        shutil.rmtree(temp_output_dir)

