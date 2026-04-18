# theme.py
def wrap(title, content):
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>{title} | Enterprise Python</title>
        <style>
            body {{ font-family: sans-serif; line-height: 1.6; margin: 40px; background: #f4f4f4; }}
            .container {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            header {{ border-bottom: 2px solid #0078d4; margin-bottom: 20px; }}
            footer {{ margin-top: 20px; font-size: 0.8em; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Corporate Dashboard</h1>
            </header>
            <main>
                {content}
            </main>
            <footer>
                &copy; 2026 Enterprise Silos Inc.
            </footer>
        </div>
    </body>
    </html>
    """