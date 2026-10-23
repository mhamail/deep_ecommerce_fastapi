from html import escape

from src.config import ADMIN_URL


def question_template(product_name: str, question: str, asked_by: str) -> str:
    """New-question notification for the shop. Everything customer-supplied
    is HTML-escaped — this goes out as an HTML email."""
    link = (
        f'<p><a href="{escape(ADMIN_URL.rstrip("/"))}/questions?status=unanswered">'
        "Answer it in the admin</a></p>"
        if ADMIN_URL
        else ""
    )
    return f"""
    <html>
    <body>
        <h2>New question on your product</h2>

        <p><strong>Product:</strong> {escape(product_name)}</p>
        <p><strong>Asked by:</strong> {escape(asked_by)}</p>

        <blockquote style="margin:0;padding:8px 12px;border-left:3px solid #ccc;">
            {escape(question)}
        </blockquote>

        {link}
    </body>
    </html>
    """
