- name: Blog Ajanini Calistir
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  run: python blog_ajani.py
