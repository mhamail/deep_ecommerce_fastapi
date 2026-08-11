// PM2 supervises `start.sh`, which runs `uv run -- uvicorn src.main:app
// --workers N`. PM2 itself doesn't speak ASGI — uvicorn is still the actual
// server; PM2 just keeps it alive, manages logs, and restarts it on crash or
// on `pm2 startOrReload`, the same role gunicorn would otherwise play here.
module.exports = {
  apps: [
    {
      name: "deep-ecom-backend",
      script: "./start.sh",
      interpreter: "bash",
      cwd: "/home/ubuntu/projects/deep_ecom/backend",

      // start.sh forks its own uvicorn worker processes — PM2 should run
      // exactly one instance of the supervisor script, not fork this itself.
      instances: 1,
      exec_mode: "fork",

      autorestart: true,
      watch: false,
      max_memory_restart: "500M",

      env: {
        PORT: "8000",
        UVICORN_WORKERS: "4",
      },

      out_file: "./logs/pm2-out.log",
      error_file: "./logs/pm2-error.log",
      merge_logs: true,
      time: true,
    },
  ],
};
