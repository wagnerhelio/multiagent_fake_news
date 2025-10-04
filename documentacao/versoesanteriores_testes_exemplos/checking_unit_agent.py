import logging
import random
import time
from typing import Dict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CheckingUnitAgent:
    def __init__(self, checker_profile: Dict):
        self.checker_profile = checker_profile
        self.id = checker_profile.get('id', 'unknown_checker')
        logging.info(f"CheckingUnitAgent {self.id} initialized with profile: {self.checker_profile}")

    def perform_check(self, content_metadata: Dict) -> Dict:
        """
        Simulates a virtual checker performing a fact-check on the content.
        Returns a simulated verdict (e.g., 'Verdadeiro', 'Falso', 'Inconclusivo')
        and a confidence score, potentially influenced by checker's reputation and content category.

        Args:
            content_metadata (Dict): Metadata of the content to be checked.

        Returns:
            Dict: A dictionary containing the checker's verdict, confidence, and ID.
        """
        content_id = content_metadata.get('id')
        content_category = content_metadata.get('category')
        checker_reputation = self.checker_profile.get('reputation', 'Bronze')
        checker_specialty = self.checker_profile.get('specialty', 'Geral')

        # Simulate check duration
        time.sleep(random.uniform(0.5, 2.0)) # Simulate work being done

        # Determine verdict based on some simplified logic
        # For prototype, let's make it somewhat random but influenced by specialty/reputation
        verdicts = ['Verdadeiro', 'Falso', 'Conteúdo Enganoso', 'Descontextualizado', 'Inconclusivo']
        
        # Higher reputation might lead to more decisive verdicts or higher confidence
        confidence_base = 0.6
        if checker_reputation == 'Bronze':
            confidence_base = 0.6
        elif checker_reputation == 'Prata':
            confidence_base = 0.75
        elif checker_reputation == 'Ouro':
            confidence_base = 0.9
        
        # If checker's specialty matches content category, higher confidence
        if checker_specialty == content_category:
            confidence_base += 0.1 # Boost confidence

        confidence = min(1.0, confidence_base + random.uniform(-0.1, 0.1))
        verdict = random.choice(verdicts)

        logging.info(f"Checker {self.id} (Rep: {checker_reputation}, Spec: {checker_specialty}) checked content {content_id} (Cat: {content_category}). Verdict: {verdict}, Confidence: {confidence:.2f}")

        return {
            'checker_id': self.id,
            'verdict': verdict,
            'confidence': confidence,
            'timestamp_checked': logging.Formatter().formatTime(logging.LogRecord(None, None, None, None, None, None, None), '%Y-%m-%d %H:%M:%S')
        }

if __name__ == '__main__':
    import time
    from ingestion_agent import IngestionAgent
    from categorization_agent import CategorizationAgent
    from priority_agent import PriorityAgent
    from checker_selection_agent import CheckerSelectionAgent
    import os
    import shutil

    # Setup temporary directory for ingested content
    temp_output_dir = "./temp_ingested_content_for_checking_unit_test"
    if os.path.exists(temp_output_dir):
        shutil.rmtree(temp_output_dir)
    os.makedirs(temp_output_dir)

    ingestion_agent = IngestionAgent(output_dir=temp_output_dir)
    categorization_agent = CategorizationAgent()
    priority_agent = PriorityAgent()
    checker_selection_agent = CheckerSelectionAgent()

    sample_text_content = {
        'type': 'text',
        'source': 'G1',
        'raw_content': 'Esta é uma notícia de teste sobre política e economia.'
    }
    ingested_info = ingestion_agent.ingest_content(sample_text_content)
    categorized_info = categorization_agent.categorize_content(ingested_info)
    prioritized_info = priority_agent.assign_priority(categorized_info)

    selected_checkers_profiles = checker_selection_agent.select_checkers(prioritized_info, num_checkers=5)
    print("\nSelected Checker Profiles:", selected_checkers_profiles)

    check_results = []
    for profile in selected_checkers_profiles:
        checking_unit = CheckingUnitAgent(profile)
        result = checking_unit.perform_check(prioritized_info)
        check_results.append(result)
    
    print("\nCheck Results:", check_results)

    # Clean up temporary files
    if os.path.exists(temp_output_dir):
        shutil.rmtree(temp_output_dir)

