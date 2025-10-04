import logging
import json
import os
import uuid
from typing import Dict, List
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ReporterAgent:
    def __init__(self, output_dir="/tmp/reports"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        logging.info(f"ReporterAgent initialized. Output directory: {self.output_dir}")

    def generate_report(self, final_content_metadata: Dict) -> Dict:
        """
        Generates a comprehensive report in JSON format based on the final content metadata.

        Args:
            final_content_metadata (Dict): The complete metadata of the content after consensus,
                                           including original content, checker results, and final verdict.

        Returns:
            Dict: A dictionary containing the path to the generated report and its content.
        """
        content_id = final_content_metadata.get('id')
        report_filename = f"report_{content_id}_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        report_filepath = os.path.join(self.output_dir, report_filename)

        report_data = {
            "report_id": str(uuid.uuid4()),
            "content_id": content_id,
            "timestamp_report_generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "original_content_info": {
                "type": final_content_metadata.get('type'),
                "source": final_content_metadata.get('source'),
                "original_content_path": final_content_metadata.get('original_content_path'),
                "raw_content_preview": self._get_content_preview(final_content_metadata.get('original_content_path'))
            },
            "categorization": {
                "category": final_content_metadata.get('category'),
                "timestamp": final_content_metadata.get('timestamp_categorized')
            },
            "priority_assignment": {
                "gut_gravidade": final_content_metadata.get('gut_gravidade'),
                "gut_urgencia": final_content_metadata.get('gut_urgencia'),
                "gut_tendencia": final_content_metadata.get('gut_tendencia'),
                "overall_priority": final_content_metadata.get('overall_priority'),
                "timestamp": final_content_metadata.get('timestamp_priority_assigned')
            },
            "checkers_involved": [
                {
                    "checker_id": res.get('checker_id'),
                    "profile": res.get('checker_profile'),
                    "verdict": res.get('verdict'),
                    "confidence": res.get('confidence'),
                    "timestamp_checked": res.get('timestamp_checked')
                } for res in final_content_metadata.get('checker_results', [])
            ],
            "consensus_result": {
                "veracity_score": final_content_metadata.get('veracity_score'),
                "final_label": final_content_metadata.get('final_label'),
                "explanation": final_content_metadata.get('consensus_explanation'),
                "timestamp": final_content_metadata.get('timestamp_consensus_reached')
            }
        }

        try:
            with open(report_filepath, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=4, ensure_ascii=False)
            logging.info(f"Report for content {content_id} generated and saved to {report_filepath}")
        except Exception as e:
            logging.error(f"Error generating report for content {content_id}: {e}")
            return {"status": "failed", "error": str(e)}

        return {
            "status": "success",
            "report_path": report_filepath,
            "report_data": report_data
        }

    def _get_content_preview(self, file_path: str, max_chars: int = 500) -> str:
        """
        Reads a preview of the original content from its file path.
        """
        if not file_path or not os.path.exists(file_path):
            return "Content file not found."
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(max_chars)
                if len(content) == max_chars:
                    content += "... (truncated)"
                return content
        except Exception as e:
            return f"Error reading content preview: {e}"

if __name__ == '__main__':
    import os
    import shutil
    import uuid
    from ingestion_agent import IngestionAgent
    from categorization_agent import CategorizationAgent
    from priority_agent import PriorityAgent
    from checker_selection_agent import CheckerSelectionAgent
    from checking_unit_agent import CheckingUnitAgent
    from consensus_agent import ConsensusAgent

    # Setup temporary directories
    temp_ingested_dir = "./temp_ingested_content_for_reporter_test"
    temp_reports_dir = "./temp_reports_for_reporter_test"
    if os.path.exists(temp_ingested_dir):
        shutil.rmtree(temp_ingested_dir)
    if os.path.exists(temp_reports_dir):
        shutil.rmtree(temp_reports_dir)
    os.makedirs(temp_ingested_dir)
    os.makedirs(temp_reports_dir)

    # Initialize agents
    ingestion_agent = IngestionAgent(output_dir=temp_ingested_dir)
    categorization_agent = CategorizationAgent()
    priority_agent = PriorityAgent()
    checker_selection_agent = CheckerSelectionAgent()
    consensus_agent = ConsensusAgent()
    reporter_agent = ReporterAgent(output_dir=temp_reports_dir)

    # Simulate a full content processing flow
    sample_content = {
        'type': 'text',
        'source': 'FakeNews.com',
        'raw_content': 'URGENTE: Vacina causa mutação genética em humanos, diz estudo secreto.'
    }

    # 1. Ingestão
    ingested_info = ingestion_agent.ingest_content(sample_content)

    # 2. Categorização
    categorized_info = categorization_agent.categorize_content(ingested_info)

    # 3. Atribuição de Prioridade
    prioritized_info = priority_agent.assign_priority(categorized_info)

    # 4. Seleção de Checadores
    selected_checkers_profiles = checker_selection_agent.select_checkers(prioritized_info, num_checkers=5)
    
    # 5. Checagem por Unidades de Checagem
    simulated_checker_results = []
    for profile in selected_checkers_profiles:
        checking_unit = CheckingUnitAgent(profile)
        result = checking_unit.perform_check(prioritized_info)
        result['checker_profile'] = profile # Add profile to result for consensus weighting
        simulated_checker_results.append(result)
    
    # Add checker results to the content metadata for the consensus agent
    prioritized_info['checker_results'] = simulated_checker_results

    # 6. Consenso
    final_content_metadata = consensus_agent.reach_consensus(prioritized_info, simulated_checker_results)

    # 7. Geração de Relatório
    report_output = reporter_agent.generate_report(final_content_metadata)
    print("\nGenerated Report Output:", report_output)

    # Clean up temporary files
    if os.path.exists(temp_ingested_dir):
        shutil.rmtree(temp_ingested_dir)
    if os.path.exists(temp_reports_dir):
        shutil.rmtree(temp_reports_dir)

