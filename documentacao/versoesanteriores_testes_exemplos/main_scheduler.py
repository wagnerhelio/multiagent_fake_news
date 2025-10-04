import logging
import time
import os
import shutil
from datetime import datetime

from agents.ingestion_agent import IngestionAgent
from agents.categorization_agent import CategorizationAgent
from agents.priority_agent import PriorityAgent
from agents.scheduler_agent import SchedulerAgent
from agents.checker_selection_agent import CheckerSelectionAgent
from agents.checking_unit_agent import CheckingUnitAgent
from agents.consensus_agent import ConsensusAgent
from agents.reporter_agent import ReporterAgent

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MultiAgentFactCheckingSystem:
    def __init__(self, base_output_dir="./system_output"):
        self.base_output_dir = os.path.join(base_output_dir, datetime.now().strftime("%Y%m%d-%H%M%S"))
        os.makedirs(self.base_output_dir, exist_ok=True)

        self.ingestion_agent = IngestionAgent(output_dir=os.path.join(self.base_output_dir, "ingested_content"))
        self.categorization_agent = CategorizationAgent()
        self.priority_agent = PriorityAgent()
        self.scheduler_agent = SchedulerAgent()
        self.checker_selection_agent = CheckerSelectionAgent()
        self.consensus_agent = ConsensusAgent()
        self.reporter_agent = ReporterAgent(output_dir=os.path.join(self.base_output_dir, "reports"))

        self.content_in_progress = {}
        logging.info(f"MultiAgentFactCheckingSystem initialized. Output will be in {self.base_output_dir}")

    def process_new_content(self, content_data: dict):
        """
        Handles the initial stages of content processing: ingestion, categorization, and priority assignment.
        Then adds the content to the scheduler's queue.
        """
        logging.info(f"[System] Receiving new content: {content_data.get('raw_content', '')[:50]}...")
        # 1. Ingestão
        ingested_info = self.ingestion_agent.ingest_content(content_data)
        if ingested_info.get('status') == 'failed':
            logging.error(f"[System] Ingestion failed for content: {content_data.get('raw_content', '')[:50]}...")
            return

        # 2. Categorização
        categorized_info = self.categorization_agent.categorize_content(ingested_info)

        # 3. Atribuição de Prioridade
        prioritized_info = self.priority_agent.assign_priority(categorized_info)
        
        self.content_in_progress[prioritized_info["id"]] = prioritized_info
        self.scheduler_agent.add_content_to_queue(prioritized_info)
        logging.info(f"[System] Content {prioritized_info['id']} processed through initial stages and added to scheduler queue.")

    def run_scheduler_cycle(self):
        """
        Executes one cycle of the intelligent scheduler:
        - Dispatches content to available checking units.
        - Simulates checking process.
        - Processes completed checks.
        """
        logging.info("[System] Running scheduler cycle...")
        
        # Dispatch content to checking units
        contents_to_dispatch = self.scheduler_agent.schedule_content()
        
        for content_metadata in contents_to_dispatch:
            content_id = content_metadata["id"]
            logging.info(f"[System] Dispatching content {content_id} for checking.")
            
            # 4. Seleção de Checadores
            selected_checkers_profiles = self.checker_selection_agent.select_checkers(content_metadata, num_checkers=5)
            
            # 5. Checagem por Unidades de Checagem (simulated)
            simulated_checker_results = []
            for profile in selected_checkers_profiles:
                checking_unit = CheckingUnitAgent(profile)
                result = checking_unit.perform_check(content_metadata) # Pass full metadata for context
                result["checker_profile"] = profile # Attach profile for consensus weighting
                simulated_checker_results.append(result)
            
            # Update content_in_progress with checker results
            self.content_in_progress[content_id]["checker_results"] = simulated_checker_results
            self.content_in_progress[content_id]["status"] = "checking_completed"
            logging.info(f"[System] Checking completed for content {content_id}. Simulating results.")

            # 6. Consenso
            final_content_metadata = self.consensus_agent.reach_consensus(self.content_in_progress[content_id], simulated_checker_results)
            self.content_in_progress[content_id] = final_content_metadata # Update with final verdict
            logging.info(f"[System] Consensus reached for content {content_id}. Final Label: {final_content_metadata.get('final_label')}")

            # 7. Geração de Relatório
            report_output = self.reporter_agent.generate_report(final_content_metadata)
            if report_output.get("status") == "success":
                logging.info(f"[System] Report generated for content {content_id} at {report_output.get('report_path')}")
            else:
                logging.error(f"[System] Failed to generate report for content {content_id}: {report_output.get('error')}")

            # Mark check as complete in scheduler
            self.scheduler_agent.complete_check(content_id, final_content_metadata)
            self.content_in_progress[content_id]["status"] = "closed"
            logging.info(f"[System] Content {content_id} fully processed and closed.")

        logging.info("[System] Scheduler cycle finished. Current queue status:")
        logging.info(self.scheduler_agent.get_queue_status())

    def get_system_status(self):
        return {
            "scheduler_status": self.scheduler_agent.get_queue_status(),
            "content_in_progress_count": len(self.content_in_progress),
            "content_in_progress_details": {cid: self.content_in_progress[cid]["status"] for cid in self.content_in_progress}
        }

    def cleanup(self):
        """
        Cleans up temporary directories created during the run.
        """
        logging.info(f"[System] Cleaning up output directory: {self.base_output_dir}")
        # shutil.rmtree(self.base_output_dir) # Uncomment to actually delete files

if __name__ == '__main__':
    system = MultiAgentFactCheckingSystem()

    # Simulate receiving multiple content items over time
    sample_contents = [
        {'type': 'text', 'source': 'G1', 'raw_content': 'Notícia de política de baixa urgência. Isso é um teste.'},
        {'type': 'text', 'source': 'Folha', 'raw_content': 'Urgente: Nova crise econômica global. Impacto severo na bolsa.'},
        {'type': 'text', 'source': 'CNN', 'raw_content': 'Descoberta médica importante na saúde. Cura para doença rara.'},
        {'type': 'text', 'source': 'ESPN', 'raw_content': 'Resultado de jogo de futebol. Time vence campeonato.'},
        {'type': 'text', 'source': 'Blog', 'raw_content': 'Fato curioso sobre o mundo. Curiosidade histórica.'},
        {'type': 'text', 'source': 'Local News', 'raw_content': 'Evento comunitário. Festival anual da cidade.'},
        {'type': 'text', 'source': 'Alert News', 'raw_content': 'Alerta de segurança pública de alta gravidade. Evacuação imediata.'},
        {'type': 'text', 'source': 'Social Media', 'raw_content': 'Boato sobre celebridade. Notícia falsa se espalhando rapidamente.'},
        {'type': 'text', 'source': 'Government', 'raw_content': 'Nova lei de impostos aprovada. Impacto na população.'},
    ]

    for i, content_data in enumerate(sample_contents):
        system.process_new_content(content_data)
        time.sleep(0.5) # Simulate content arriving over time

    logging.info("\n--- Initial System Status ---")
    logging.info(system.get_system_status())

    # Run scheduler cycles until all content is processed or a certain number of cycles
    max_cycles = 10
    cycle_count = 0
    while any(status != "closed" for status in system.get_system_status()["content_in_progress_details"].values()) and cycle_count < max_cycles:
        logging.info(f"\n--- Running Scheduler Cycle {cycle_count + 1} ---")
        system.run_scheduler_cycle()
        time.sleep(1) # Simulate time passing between cycles
        cycle_count += 1

    logging.info("\n--- Final System Status ---")
    logging.info(system.get_system_status())

    # system.cleanup() # Uncomment to clean up output files

