# RS Template Mobile App

A React Native/Expo mobile application template for testing the RS Template Cloud Run services.

## Overview

This mobile app provides a simple interface to interact with the RS Template backend services deployed on Google Cloud Run. It's configured specifically for iOS simulator testing and includes basic authentication, API integration, and service testing capabilities.

## Prerequisites

- Node.js 18+ and npm
- Xcode (for iOS simulator)
- Expo CLI: `npm install -g expo-cli`
- EAS CLI (optional, for builds): `npm install -g eas-cli`

## Installation

```bash
# Navigate to the mobile directory
cd mobile

# Install dependencies
npm install

# Install iOS pods (if running on Mac)
cd ios && pod install && cd ..
```

## Running the App

### Local Development Setup

1. **Start the backend services first:**
```bash
# From the project root directory
make run-local
# or
docker-compose up -d
```

2. **Run the mobile app:**
```bash
cd mobile
npm install  # First time only
npm run ios  # For iOS simulator
```

**Note**: The app automatically detects your machine's IP address for connecting to local Docker services. If you have connection issues:

1. Create a `.env.local` file (copy from `.env.local.example`)
2. Set your machine's IP explicitly:
   ```
   EXPO_PUBLIC_API_URL=http://YOUR_IP:8000
   ```
3. Find your IP with: `ifconfig | grep "inet " | grep -v 127.0.0.1`

### Against Staging Environment

```bash
# Run iOS simulator against staging services
npm run ios:staging
```

### Against Production Environment

```bash
# Run iOS simulator against production services  
npm run ios:production
```

## Environment Configuration

The app uses environment variables to configure the API endpoint:

- **Local**: `http://localhost:8000` (default)
- **Staging**: `https://rs-template-staging-gateway-799562302.us-central1.run.app`
- **Production**: `https://rs-template-production-gateway-799562302.us-central1.run.app`

## Features

### Authentication
- Mock authentication system (ready to integrate with real auth)
- Login/Sign Up screens
- Persistent session storage

### API Integration
- Health check endpoint testing
- AI service integration
- File upload/download testing (pre-signed URLs)
- Automatic authorization header injection

### Screens
- **Login**: Authentication interface
- **Home**: Service status and testing capabilities
- **Profile**: User information and account management
- **Settings**: App preferences and API configuration display

## Project Structure

```
mobile/
├── App.tsx                 # Main app component with navigation
├── src/
│   ├── contexts/          # React contexts (Auth, API)
│   ├── screens/           # App screens
│   │   ├── LoginScreen.tsx
│   │   ├── HomeScreen.tsx
│   │   ├── ProfileScreen.tsx
│   │   ├── SettingsScreen.tsx
│   │   └── LoadingScreen.tsx
│   └── services/          # API service modules
├── assets/                # Images and static assets
├── app.json              # Expo configuration
├── eas.json              # EAS Build configuration
└── package.json          # Dependencies and scripts
```

## Testing Features

### Health Check
The Home screen automatically checks the gateway health endpoint on load and displays:
- Service status
- Version information
- Environment (staging/production)

### AI Service Test
Tests the AI chat endpoint with a sample request and displays the response.

### File Upload Test
Placeholder for testing file upload functionality with the storage service.

## Building for Simulator

### Local Build

```bash
# Build for iOS simulator locally
npm run build:ios:simulator
```

### EAS Build

```bash
# Login to EAS
eas login

# Build for development (simulator)
eas build --platform ios --profile development
```

## Mock Authentication

The app includes a mock authentication system for testing. In production, replace the mock implementation in `AuthContext.tsx` with real API calls to your authentication service.

**Mock Credentials**: Any email/password combination will work for testing.

## API Integration

The `ApiContext` provides methods for all HTTP operations:

```typescript
const { get, post, put, delete, uploadFile } = useApi();

// Example usage
const health = await get('/health');
const response = await post('/ai/chat', { message: 'Hello' });
```

## Customization

### Change API Endpoints
Update the URLs in:
- `package.json` scripts
- `eas.json` environment variables

### Add New Screens
1. Create screen component in `src/screens/`
2. Add to navigation in `App.tsx`
3. Update tab navigator if needed

### Integrate Real Authentication
Replace mock auth in `src/contexts/AuthContext.tsx` with your authentication provider (e.g., Clerk, Auth0, Firebase).

## Troubleshooting

### iOS Simulator Not Opening
```bash
# Reset Expo cache
npx expo start -c

# Ensure Xcode is installed
xcode-select --install
```

### API Connection Issues
- Check that backend services are deployed and running
- Verify environment URLs in package.json scripts
- Check network connectivity in simulator

### Build Errors
```bash
# Clear all caches
npm run clean
rm -rf node_modules
npm install
```

## Notes

- This app is configured for iOS simulator testing only
- For Android support, additional configuration may be needed
- The app uses Expo SDK 53 and React Native 0.79.5
- TypeScript is configured with strict mode enabled

## License

MIT