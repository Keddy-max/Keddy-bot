# Keddy Embeddable Website Chat Widget

## How to embed

Add this single script tag anywhere on your site:

```html
<script src="https://YOUR-RENDER-APP.onrender.com/static/widget.js"></script>
```

No other HTML is required.

## API endpoint

The widget calls:

- `POST /chat`

Request:

```json
{ "message": "Hello" }
```

Response:

```json
{ "reply": "Hello! How can I help you?" }
```

