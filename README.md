# Voice Assistant Demo

A FastAPI application for handling package delivery scheduling via voice assistant integration.

## Setup

### Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` and add your actual Retell API key:
   ```
   RETELL_API_KEY=your_actual_api_key_here
   ```

4. Run the application:
   ```bash
   uvicorn app.app:app --reload
   ```

### Docker Deployment

Build and run with Docker (no need to create .env file):

```bash
# Build the image
docker build -t voice-assistant-demo .

# Run the container
docker run -p 8000:8000 -e RETELL_API_KEY=your_actual_api_key_here voice-assistant-demo
```

## Environment Variables

- `RETELL_API_KEY`: Required. Your Retell AI API key for webhook signature verification.

## API Endpoints

- `POST /verify`: Verify package tracking information
- `POST /update_date`: Update package delivery schedule
- `POST /finish_call`: Log call transcript and send confirmation email