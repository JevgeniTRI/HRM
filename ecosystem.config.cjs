module.exports = {
  apps: [
    {
      name: 'jevgeniworks-hrm-api',
      cwd: '/data01/virt146264/domeenid/www.jevgeniworks.ee/backend',
      script: '/data01/virt146264/domeenid/www.jevgeniworks.ee/backend/.venv/bin/python',
      args: '-m uvicorn app.main:app --host 127.2.98.104 --port 18080 --proxy-headers --forwarded-allow-ips=*',
      interpreter: 'none',
      autorestart: true,
      max_memory_restart: '256M',
      env: {
        PYTHONUNBUFFERED: '1',
      },
    },
  ],
};
