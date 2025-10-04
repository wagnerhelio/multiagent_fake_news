import logging
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PriorityAgent:
    def __init__(self):
        logging.info("PriorityAgent initialized.")

    def assign_priority(self, content_metadata: dict) -> dict:
        """
        Simulates the assignment of a GUT (Gravidade, Urgência, Tendência) score to content.
        For this prototype, it assigns random GUT scores, possibly influenced by category.

        Args:
            content_metadata (dict): Metadata from the CategorizationAgent, including the category.

        Returns:
            dict: Updated content metadata with assigned GUT scores and overall priority.
        """
        content_id = content_metadata.get('id')
        category = content_metadata.get('category', 'Geral')

        # Simulate GUT score assignment (1-5 for each component)
        # Gravidade (Severity): How serious is the impact if the content is false/misleading?
        # Urgência (Urgency): How quickly does this content need to be checked?
        # Tendência (Trend): How likely is this content to spread or cause further issues?

        gravidade = random.randint(1, 5)
        urgencia = random.randint(1, 5)
        tendencia = random.randint(1, 5)

        # Example: Higher priority for 'Política' or 'Saúde' categories
        if category in ['Política', 'Saúde']:
            gravidade = random.randint(3, 5) # More likely to be high severity
            urgencia = random.randint(3, 5)  # More likely to be urgent

        # Calculate overall priority (e.g., sum of GUT scores)
        overall_priority = gravidade + urgencia + tendencia

        logging.info(f"Content {content_id} (Category: {category}) assigned GUT: G={gravidade}, U={urgencia}, T={tendencia}, Overall Priority: {overall_priority}")

        return {
            **content_metadata,
            'status': 'priority_assigned',
            'gut_gravidade': gravidade,
            'gut_urgencia': urgencia,
            'gut_tendencia': tendencia,
            'overall_priority': overall_priority,
            'timestamp_priority_assigned': logging.Formatter().formatTime(logging.LogRecord(None, None, None, None, None, None, None), '%Y-%m-%d %H:%M:%S')
        }

if __name__ == '__main__':
    # Simulate the flow from Ingestion -> Categorization -> Priority Assignment
    from ingestion_agent import IngestionAgent
    from categorization_agent import CategorizationAgent
    import os
    import shutil

    # Setup temporary directory for ingested content
    temp_output_dir = "./temp_ingested_content_for_priority_test"
    if os.path.exists(temp_output_dir):
        shutil.rmtree(temp_output_dir)
    os.makedirs(temp_output_dir)

    ingestion_agent = IngestionAgent(output_dir=temp_output_dir)
    categorization_agent = CategorizationAgent()
    priority_agent = PriorityAgent()

    sample_text_content_pol = {
        'type': 'text',
        'source': 'News Outlet',
        'raw_content': 'Presidente anuncia novas medidas econômicas para o país.'
    }
    ingested_info_pol = ingestion_agent.ingest_content(sample_text_content_pol)
    categorized_info_pol = categorization_agent.categorize_content(ingested_info_pol)
    prioritized_info_pol = priority_agent.assign_priority(categorized_info_pol)
    print("Prioritized Political Content:", prioritized_info_pol)

    sample_text_content_sports = {
        'type': 'text',
        'source': 'Sports Blog',
        'raw_content': 'Time de futebol vence campeonato regional com gol no último minuto.'
    }
    ingested_info_sports = ingestion_agent.ingest_content(sample_text_content_sports)
    categorized_info_sports = categorization_agent.categorize_content(ingested_info_sports)
    prioritized_info_sports = priority_agent.assign_priority(categorized_info_sports)
    print("Prioritized Sports Content:", prioritized_info_sports)

    # Clean up temporary files
    if os.path.exists(temp_output_dir):
        shutil.rmtree(temp_output_dir)

