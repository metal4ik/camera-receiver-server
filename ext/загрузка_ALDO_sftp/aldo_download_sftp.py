import os
import paramiko
import datetime
import logging
from stat import S_ISDIR

# Настроим логирование
logging.basicConfig(
    filename='sftp_fetch.log',  # Лог-файл будет находиться в том же каталоге
    level=logging.INFO,  # Уровень логирования
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def sftp_fetch_files(host, port, username, remote_dir, local_dir, days=7):
    cutoff_time = datetime.datetime.now() - datetime.timedelta(days=days)
    
    # Загружаем ключ
    key = paramiko.RSAKey.from_private_key_file("id_rsa")
    
    # Устанавливаем соединение с SFTP
    transport = paramiko.Transport((host, port))
    transport.connect(username=username, pkey=key)
    sftp = paramiko.SFTPClient.from_transport(transport)
    
    def download_files(remote_path, local_path):
        os.makedirs(local_path, exist_ok=True)
        
        for item in sftp.listdir_attr(remote_path):
            item_path = f"{remote_path}/{item.filename}"
            local_item_path = os.path.join(local_path, item.filename)
            
            if S_ISDIR(item.st_mode):
                download_files(item_path, local_item_path)
            else:
                file_mtime = datetime.datetime.fromtimestamp(item.st_mtime)
                if file_mtime >= cutoff_time:
                    if not os.path.exists(local_item_path):
                        try:
                            logging.info(f"Downloading: {item_path} -> {local_item_path}")
                            print(f"Downloading: {item_path} -> {local_item_path}")
                            sftp.get(item_path, local_item_path)
                            logging.info(f"Downloaded successfully: {item_path} -> {local_item_path}")
                        except Exception as e:
                            logging.error(f"Error downloading {item_path}: {e}")
                            print(f"Error downloading {item_path}: {e}")
                    else:
                        logging.info(f"File already exists, skipping: {local_item_path}")
                        print(f"File already exists, skipping: {local_item_path}")
    
    download_files(remote_dir, local_dir)
    
    sftp.close()
    transport.close()
    logging.info("Download completed.")
    print("Download completed.")

# Пример вызова функции
sftp_fetch_files(
    host='s-01ef795d220a485f9.server.transfer.ca-central-1.amazonaws.com',
    port=22,
    username='fran_200134',
    remote_dir='/prod/talend2franchisee/inbound',
    local_dir='D:/ALDO_Download/download',  
    days=29  # Скачивать файлы за последние Х дней
)
