global:
  scrape_interval: 5s

scrape_configs:
  - job_name: 'load_generators'
    static_configs:
      {% for target in targets %}
      - targets: ['{{ target }}']
      {% endfor %}
