import os
import requests
import gzip
import shutil
from pathlib import Path
from tqdm import tqdm

def download_and_extract_alphamissense(dest_folder: Path):
    """
    Baixa o dataset público AlphaMissense do bucket do Google Cloud Storage
    e o descompacta simultaneamente para economizar espaço em disco intermediário.
    """
    url = "https://zenodo.org/records/8208688/files/AlphaMissense_hg38.tsv.gz"
    dest_folder.mkdir(parents=True, exist_ok=True)
    
    gz_path = dest_folder / "AlphaMissense_hg38.tsv.gz"
    tsv_path = dest_folder / "AlphaMissense_hg38.tsv"
    
    if tsv_path.exists():
        print(f"O arquivo {tsv_path} já existe. Ignorando download.")
        return
        
    print(f"Iniciando download do AlphaMissense: {url}")
    print("Aviso: O arquivo compactado possui ~1.5GB. A descompactação gerará ~20GB de dados.")
    
    try:
        # Faz o streaming do download com barra de progresso
        response = requests.get(url, stream=True)
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        
        with open(gz_path, 'wb') as f_out, tqdm(
            desc="Baixando AlphaMissense (.gz)",
            total=total_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for chunk in response.iter_content(chunk_size=8192):
                size = f_out.write(chunk)
                bar.update(size)
                
        print("\nDownload concluído! Iniciando descompactação (isso pode demorar minutos)...")
        
        with gzip.open(gz_path, 'rb') as f_in:
            with open(tsv_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
                
        print(f"Descompactacao concluida! Arquivo pronto em: {tsv_path}")
        
        # Opcional: remover o .gz para limpar o Google Drive
        os.remove(gz_path)
        print(f"Arquivo temporario {gz_path} removido para economizar espaco.")
        
    except Exception as e:
        print(f"Erro critico no download: {e}")

if __name__ == "__main__":
    import sys
    # Se o usuário não passar argumento, assume a pasta do Google Drive
    target_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"G:\Meu Drive\IA_dos_numeros_primos_Cloud")
    download_and_extract_alphamissense(target_dir)
