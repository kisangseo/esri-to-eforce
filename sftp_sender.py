import os
import paramiko
from io import BytesIO


def send_xml_to_eforce(xml_bytes: bytes, filename: str):
    host = os.getenv("EFORCE_SFTP_HOST")
    user = os.getenv("EFORCE_SFTP_USER")
    password = os.getenv("EFORCE_SFTP_PASSWORD")
    port = int(os.getenv("EFORCE_SFTP_PORT", "22"))

    if not all([host, user, password]):
        raise RuntimeError("Missing EFORCE SFTP environment variables")

    transport = paramiko.Transport((host, port))
    transport.connect(username=user, password=password)

    sftp = paramiko.SFTPClient.from_transport(transport)

    # Upload to root directory unless EFORCE specifies otherwise
    with sftp.file(filename, "wb") as remote_file:
        remote_file.write(xml_bytes)

    sftp.close()
    transport.close()
