import logging
import os
import uuid
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class IngestionAgent: 
    def __init__(self, output_dir="/tmp/ingested_content"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        logging.info(f"IngestionAgent initialized. Output directory: {self.output_dir}")

    def ingest_content(self, content_data: dict) -> dict:
        """
        Simulates the ingestion of multimedia content.
        In a real scenario, this would handle file uploads, API calls, etc.
        For this prototype, it will simulate processing and return metadata.

        Args:
            content_data (dict): A dictionary containing content information, e.g.,
                                 {'type': 'text', 'source': 'G1', 'raw_content': '...'}

        Returns:
            dict: A dictionary with processed content metadata, including a unique ID and path.
        """
        content_id = str(uuid.uuid4())
        content_type = content_data.get('type', 'unknown')
        source = content_data.get('source', 'unknown')
        raw_content = content_data.get('raw_content', '')

        # Simulate saving content to a file (e.g., for later processing)
        file_extension = {
            'text': '.txt',
            'image': '.jpg',
            'audio': '.mp3',
            'video': '.mp4'
        }.get(content_type, '.bin')

        file_name = f"{content_id}{file_extension}"
        file_path = os.path.join(self.output_dir, file_name)

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(raw_content)
            logging.info(f"Content {content_id} (type: {content_type}) ingested and saved to {file_path}")
        except Exception as e:
            logging.error(f"Error saving content {content_id}: {e}")
            return {'status': 'failed', 'error': str(e)}

        processed_metadata = {
            'id': content_id,
            'type': content_type,
            'source': source,
            'original_content_path': file_path, # Path to the simulated raw content
            'status': 'ingested',
            'timestamp': logging.Formatter().formatTime(logging.LogRecord(None, None, None, None, None, None, None), '%Y-%m-%d %H:%M:%S')
        }
        return processed_metadata

if __name__ == '__main__':
    agent = IngestionAgent()
    sample_text_content = {
        'type': 'text',
        'source': 'G1',
        'raw_content': 'Esta é uma notícia de teste sobre política e economia.'
    }
    ingested_info = agent.ingest_content(sample_text_content)
    print(ingested_info)

    sample_image_content = {
        'type': 'image',
        'source': 'Instagram',
        'raw_content': 'Simulação de dados binários de uma imagem.'
    }
    ingested_info_image = agent.ingest_content(sample_image_content)
    print(ingested_info_image)

