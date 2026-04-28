X_POST_TEMPLATE = "{hook}\n\n{body}\n\n{closing}"

NEWSLETTER_TEMPLATE = """
# {title}
### {subtitle}

{opening}

---

{deliverable}

---

{closing}

---
{cta}
""".strip()
