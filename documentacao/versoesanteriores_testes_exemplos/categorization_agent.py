import logging
import os
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CategorizationAgent:
    def __init__(self):
        self.categories = ["Política", "Saúde", "Economia", "Mundo", "Esportes", "Geral"]
        logging.info("CategorizationAgent initialized.")

    def categorize_content(self, content_metadata: dict) -> dict:
        """
        Simulates the categorization of content using a trained AI.
        For this prototype, it assigns a random category or a category based on keywords.

        Args:
            content_metadata (dict): Metadata from the IngestionAgent, including 'raw_content'.

        Returns:
            dict: Updated content metadata with an assigned category.
        """
        content_id = content_metadata.get('id')
        raw_content_path = content_metadata.get('original_content_path')
        content_type = content_metadata.get('type')

        if not raw_content_path or not os.path.exists(raw_content_path):
            logging.error(f"Content file not found for ID {content_id} at {raw_content_path}")
            return {**content_metadata, 'status': 'categorization_failed', 'category': 'unknown'}

        try:
            with open(raw_content_path, 'r', encoding='utf-8') as f:
                raw_content = f.read()
        except Exception as e:
            logging.error(f"Error reading raw content for ID {content_id}: {e}")
            return {**content_metadata, 'status': 'categorization_failed', 'category': 'unknown'}

        # Simulate AI categorization based on keywords or randomly
        assigned_category = "Geral"
        if "política" in raw_content.lower() or "governo" in raw_content.lower() or "eleição" in raw_content.lower():
            assigned_category = "Política"
        elif "saúde" in raw_content.lower() or "doença" in raw_content.lower() or "hospital" in raw_content.lower():
            assigned_category = "Saúde"
        elif "economia" in raw_content.lower() or "mercado" in raw_content.lower() or "finanças" in raw_content.lower():
            assigned_category = "Economia"
        elif "esporte" in raw_content.lower() or "futebol" in raw_content.lower() or "olimpíadas" in raw_content.lower():
            assigned_category = "Esportes"
        else:
            assigned_category = random.choice(self.categories) # Fallback to random if no keywords match

        logging.info(f"Content {content_id} (type: {content_type}) categorized as: {assigned_category}")

        return {
            **content_metadata,
            'status': 'categorized',
            'category': assigned_category,
            'timestamp_categorized': logging.Formatter().formatTime(logging.LogRecord(None, None, None, None, None, None, None), '%Y-%m-%d %H:%M:%S')
        }

if __name__ == '__main__':
    # This part would typically be called by another agent or the scheduler
    # For demonstration, we simulate an ingested content metadata
    from ingestion_agent import IngestionAgent

    ingestion_agent = IngestionAgent(output_dir="./temp_ingested_content")
    sample_text_content = {
        'type': 'text',
        'source': 'G1',
        'raw_content': 'Esta é uma notícia de teste sobre política e economia.'
    }
    ingested_info = ingestion_agent.ingest_content(sample_text_content)
    print("Ingested Info:", ingested_info)

    categorization_agent = CategorizationAgent()
    categorized_info = categorization_agent.categorize_content(ingested_info)
    print("Categorized Info:", categorized_info)

    sample_health_content = {
        'type': 'text',
        'source': 'Blog Saúde',
        'raw_content': 'Novas descobertas na área da saúde e bem-estar.'
    }
    ingested_health_info = ingestion_agent.ingest_content(sample_health_content)
    categorized_health_info = categorization_agent.categorize_content(ingested_health_info)
    print("Categorized Health Info:", categorized_health_info)

    # Clean up temporary files
    if os.path.exists("./temp_ingested_content"):
        import shutil
        shutil.rmtree("./temp_ingested_content")

