import subprocess
result = subprocess.run(['gcloud config get-value project'], shell=True, capture_output=True)
project_id = str('url_config_' + result.stdout.decode()).strip()
print(project_id + 'xxx')