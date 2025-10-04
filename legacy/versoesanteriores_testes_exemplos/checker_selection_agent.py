import logging
import random
from typing import List, Dict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CheckerSelectionAgent:
    def __init__(self):
        # Simulate a pool of virtual checkers with different specializations and reputations
        self.checker_pool = [
            {"id": "checker_001", "type": "specific", "specialty": "Política", "reputation": "Ouro"},
            {"id": "checker_002", "type": "specific", "specialty": "Política", "reputation": "Prata"},
            {"id": "checker_003", "type": "specific", "specialty": "Política", "reputation": "Bronze"},
            {"id": "checker_004", "type": "specific", "specialty": "Saúde", "reputation": "Ouro"},
            {"id": "checker_005", "type": "specific", "specialty": "Saúde", "reputation": "Prata"},
            {"id": "checker_006", "type": "specific", "specialty": "Economia", "reputation": "Ouro"},
            {"id": "checker_007", "type": "specific", "specialty": "Economia", "reputation": "Prata"},
            {"id": "checker_008", "type": "independent", "specialty": "Geral", "reputation": "Ouro"},
            {"id": "checker_009", "type": "independent", "specialty": "Geral", "reputation": "Prata"},
            {"id": "checker_010", "type": "independent", "specialty": "Geral", "reputation": "Bronze"},
            {"id": "checker_011", "type": "specific", "specialty": "Mundo", "reputation": "Ouro"},
            {"id": "checker_012", "type": "specific", "specialty": "Esportes", "reputation": "Prata"},
            {"id": "checker_013", "type": "independent", "specialty": "Geral", "reputation": "Ouro"},
            {"id": "checker_014", "type": "specific", "specialty": "Política", "reputation": "Ouro"},
            {"id": "checker_015", "type": "specific", "specialty": "Saúde", "reputation": "Prata"},
        ]
        logging.info("CheckerSelectionAgent initialized with a pool of virtual checkers.")

    def select_checkers(self, content_metadata: Dict, num_checkers: int = 5) -> List[Dict]:
        """
        Selects a group of virtual checkers based on content category and priority.
        Ensures a mix of specific and independent checkers.

        Args:
            content_metadata (Dict): Metadata of the content to be checked, including category.
            num_checkers (int): The total number of checkers to select (default is 5).

        Returns:
            List[Dict]: A list of selected checker profiles.
        """
        category = content_metadata.get('category', 'Geral')
        selected_checkers = []

        # Prioritize specific checkers for the content's category
        specific_checkers_candidates = [c for c in self.checker_pool if c["type"] == "specific" and c["specialty"] == category]
        # Fallback to general specific checkers if not enough specialized ones
        if len(specific_checkers_candidates) < num_checkers // 2:
            specific_checkers_candidates.extend([c for c in self.checker_pool if c["type"] == "specific" and c["specialty"] == "Geral"])
        
        # Independent checkers are always general
        independent_checkers_candidates = [c for c in self.checker_pool if c["type"] == "independent"]

        # Ensure at least 2-4 specific and 2-4 independent checkers, summing to num_checkers
        # For simplicity in prototype, we'll try to get a balanced mix, ensuring 5 total.
        # A more robust implementation would handle edge cases of checker availability.

        # Try to get 3 specific and 2 independent, or 2 specific and 3 independent
        num_specific_needed = min(random.randint(2, 3), len(specific_checkers_candidates))
        num_independent_needed = num_checkers - num_specific_needed

        # Adjust if not enough independent checkers
        if num_independent_needed > len(independent_checkers_candidates):
            num_independent_needed = len(independent_checkers_candidates)
            num_specific_needed = num_checkers - num_independent_needed
        
        # Adjust if not enough specific checkers
        if num_specific_needed > len(specific_checkers_candidates):
            num_specific_needed = len(specific_checkers_candidates)
            num_independent_needed = num_checkers - num_specific_needed

        selected_specific = random.sample(specific_checkers_candidates, num_specific_needed)
        selected_independent = random.sample(independent_checkers_candidates, num_independent_needed)

        selected_checkers = selected_specific + selected_independent
        
        # If still not 5, fill with any available checkers (less ideal but ensures 5 for prototype)
        if len(selected_checkers) < num_checkers:
            remaining_needed = num_checkers - len(selected_checkers)
            all_other_checkers = [c for c in self.checker_pool if c not in selected_checkers]
            selected_checkers.extend(random.sample(all_other_checkers, min(remaining_needed, len(all_other_checkers))))

        logging.info(f"Selected {len(selected_checkers)} checkers for content {content_metadata.get('id')}: {[c['id'] for c in selected_checkers]}")
        return selected_checkers

if __name__ == '__main__':
    # Simulate the flow to test checker selection
    from ingestion_agent import IngestionAgent
    from categorization_agent import CategorizationAgent
    from priority_agent import PriorityAgent
    import os
    import shutil

    # Setup temporary directory for ingested content
    temp_output_dir = "./temp_ingested_content_for_checker_test"
    if os.path.exists(temp_output_dir):
        shutil.rmtree(temp_output_dir)
    os.makedirs(temp_output_dir)

    ingestion_agent = IngestionAgent(output_dir=temp_output_dir)
    categorization_agent = CategorizationAgent()
    priority_agent = PriorityAgent()
    checker_selection_agent = CheckerSelectionAgent()

    sample_text_content_pol = {
        'type': 'text',
        'source': 'News Outlet',
        'raw_content': 'Presidente anuncia novas medidas econômicas para o país.'
    }
    ingested_info_pol = ingestion_agent.ingest_content(sample_text_content_pol)
    categorized_info_pol = categorization_agent.categorize_content(ingested_info_pol)
    prioritized_info_pol = priority_agent.assign_priority(categorized_info_pol)
    print("Prioritized Political Content:", prioritized_info_pol)

    selected_checkers = checker_selection_agent.select_checkers(prioritized_info_pol)
    print("Selected Checkers:", selected_checkers)

    sample_text_content_health = {
        'type': 'text',
        'source': 'Health Blog',
        'raw_content': 'Descoberta de nova vacina contra doença rara.'
    }
    ingested_info_health = ingestion_agent.ingest_content(sample_text_content_health)
    categorized_info_health = categorization_agent.categorize_content(ingested_info_health)
    prioritized_info_health = priority_agent.assign_priority(categorized_info_health)
    print("Prioritized Health Content:", prioritized_info_health)

    selected_checkers_health = checker_selection_agent.select_checkers(prioritized_info_health)
    print("Selected Checkers for Health:", selected_checkers_health)

    # Clean up temporary files
    if os.path.exists(temp_output_dir):
        shutil.rmtree(temp_output_dir)

