import logging
import numpy as np
from scipy.stats import norm
from typing import List, Dict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ConsensusAgent:
    def __init__(self):
        logging.info("ConsensusAgent initialized.")

    def _probit_like_aggregation(self, checker_results: List[Dict]) -> (float, str):
        """
        Aggregates checker results using a simplified probit-like logic.
        Each checker's verdict is converted to a numerical score, weighted by confidence and reputation.
        
        For simplicity, we'll map verdicts to numerical values:
        - Verdadeiro: 1.0
        - Falso: -1.0
        - Conteúdo Enganoso: -0.5
        - Descontextualizado: -0.2
        - Inconclusivo: 0.0
        
        Reputation weights:
        - Ouro: 1.5
        - Prata: 1.2
        - Bronze: 1.0
        """
        verdict_mapping = {
            'Verdadeiro': 1.0,
            'Falso': -1.0,
            'Conteúdo Enganoso': -0.5,
            'Descontextualizado': -0.2,
            'Inconclusivo': 0.0
        }

        reputation_weights = {
            'Ouro': 1.5,
            'Prata': 1.2,
            'Bronze': 1.0
        }

        weighted_scores = []
        total_weight = 0.0

        for result in checker_results:
            verdict_score = verdict_mapping.get(result.get('verdict'), 0.0)
            confidence = result.get('confidence', 0.5)
            checker_reputation = result.get('checker_profile', {}).get('reputation', 'Bronze')
            
            weight = confidence * reputation_weights.get(checker_reputation, 1.0)
            weighted_scores.append(verdict_score * weight)
            total_weight += weight

        if total_weight == 0:
            return 0.0, 'Inconclusivo'

        average_weighted_score = sum(weighted_scores) / total_weight

        # Convert average score back to a final label
        if average_weighted_score >= 0.7:
            final_label = 'Verdadeiro'
        elif average_weighted_score >= 0.3:
            final_label = 'Predominantemente Verdadeiro'
        elif average_weighted_score > -0.3:
            final_label = 'Inconclusivo'
        elif average_weighted_score > -0.7:
            final_label = 'Predominantemente Falso'
        else:
            final_label = 'Falso'
        
        # The score itself can be the probit score, scaled to 0-1 for easier interpretation
        # Using a sigmoid-like transformation for a final score between 0 and 1
        # This is a simplification, true probit involves CDF of normal distribution
        probit_score = norm.cdf(average_weighted_score) # Maps any real number to 0-1

        return probit_score, final_label

    def reach_consensus(self, content_metadata: Dict, checker_results: List[Dict]) -> Dict:
        """
        Combines individual checker verdicts into a final consensus.

        Args:
            content_metadata (Dict): Original content metadata.
            checker_results (List[Dict]): A list of results from individual checking units.

        Returns:
            Dict: Updated content metadata with final veracity score and label.
        """
        content_id = content_metadata.get('id')
        
        if not checker_results:
            logging.warning(f"No checker results provided for content {content_id}. Returning inconclusive.")
            return {
                **content_metadata,
                'status': 'consensus_failed',
                'veracity_score': 0.5,
                'final_label': 'Inconclusivo',
                'consensus_explanation': 'No checker results to form consensus.'
            }

        veracity_score, final_label = self._probit_like_aggregation(checker_results)

        # Generate a simple explanation for the prototype
        explanation = f"Consenso alcançado com base em {len(checker_results)} pareceres. Score médio ponderado: {veracity_score:.2f}."
        
        logging.info(f"Content {content_id} consensus reached: Score={veracity_score:.2f}, Label=\"{final_label}\"")

        return {
            **content_metadata,
            'status': 'consensus_reached',
            'veracity_score': veracity_score,
            'final_label': final_label,
            'checker_results': checker_results, # Keep individual results for reporting
            'consensus_explanation': explanation,
            'timestamp_consensus_reached': logging.Formatter().formatTime(logging.LogRecord(None, None, None, None, None, None, None), '%Y-%m-%d %H:%M:%S')
        }

if __name__ == '__main__':
    # Simulate the full pipeline for testing the consensus agent
    import time
    from ingestion_agent import IngestionAgent
    from categorization_agent import CategorizationAgent
    from priority_agent import PriorityAgent
    from checker_selection_agent import CheckerSelectionAgent
    from checking_unit_agent import CheckingUnitAgent
    import os
    import shutil

    # Setup temporary directory for ingested content
    temp_output_dir = "./temp_ingested_content_for_consensus_test"
    if os.path.exists(temp_output_dir):
        shutil.rmtree(temp_output_dir)
    os.makedirs(temp_output_dir)

    ingestion_agent = IngestionAgent(output_dir=temp_output_dir)
    categorization_agent = CategorizationAgent()
    priority_agent = PriorityAgent()
    checker_selection_agent = CheckerSelectionAgent()
    consensus_agent = ConsensusAgent()

    sample_text_content = {
        'type': 'text',
        'source': 'G1',
        'raw_content': 'Esta é uma notícia de teste sobre política e economia. Parece ser falsa.'
    }
    ingested_info = ingestion_agent.ingest_content(sample_text_content)
    categorized_info = categorization_agent.categorize_content(ingested_info)
    prioritized_info = priority_agent.assign_priority(categorized_info)

    selected_checkers_profiles = checker_selection_agent.select_checkers(prioritized_info, num_checkers=5)
    
    # Simulate checker results
    simulated_checker_results = []
    for profile in selected_checkers_profiles:
        checking_unit = CheckingUnitAgent(profile)
        result = checking_unit.perform_check(prioritized_info)
        result['checker_profile'] = profile # Add profile to result for consensus weighting
        simulated_checker_results.append(result)
    
    print("\nSimulated Checker Results:", simulated_checker_results)

    consensus_result = consensus_agent.reach_consensus(prioritized_info, simulated_checker_results)
    print("\nConsensus Result:", consensus_result)

    # Clean up temporary files
    if os.path.exists(temp_output_dir):
        shutil.rmtree(temp_output_dir)

