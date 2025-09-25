import os; from dotenv import load_dotenv; load_dotenv(); print(f\
TENANT_ID:
os.getenv('TENANT_ID')
\); print(f\DATA_AGENT_URL:
os.getenv('DATA_AGENT_URL')
\)
