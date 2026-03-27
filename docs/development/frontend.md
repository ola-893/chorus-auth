# Frontend Development Guide

## Overview

The Chorus frontend is a React application providing a comprehensive dashboard for monitoring agent interactions, system health, and alerts. It is designed with a modern aesthetic using glass morphism and neon accents.

## Getting Started

This project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app).

### Prerequisites
- Node.js 18+
- npm

### Installation & Run

```bash
cd frontend
npm install
npm start
```

Runs the app in development mode at [http://localhost:3000](http://localhost:3000).

### Build for Production

```bash
npm run build
```

Builds the app to the `build` folder.

## UI/UX Enhancements

The dashboard features a "Cyber-Physical System" aesthetic:

### Visual Design
- **Color Palette**: Neon Green (#00ff88), Cyan Blue (#00ccff), Hot Pink (#ff0044).
- **Glass Morphism**: Translucent backgrounds with backdrop blur.
- **Typography**: Space Grotesk (Headings) and Inter (Body).
- **Animations**: Smooth transitions (0.4s), hover lift effects, and staggered entry.

### Key Components

#### 1. Dashboard Header
- Neon title with pulsing glow.
- Connection status indicators.

#### 2. System Health Cards
- Real-time status with 3D hover effects.
- Animated progress bars for system load.

#### 3. Agent Cards
- Visual trust score indicators.
- Status badges (Active/Quarantined).
- Resource usage bars.

#### 4. Conflict Predictions
- Risk-based coloring (Green/Yellow/Red).
- Probability visualization.

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── dashboard/    # Main dashboard widgets
│   │   ├── layout/       # Header, Footer, Sidebar
│   │   └── common/       # Reusable UI components
│   ├── services/         # API integration (WebSocket, HTTP)
│   ├── hooks/            # Custom React hooks
│   ├── styles/           # Global styles and themes
│   └── App.tsx           # Main application entry
├── public/
└── package.json
```

## Styling Guide

- **CSS Variables**: Defined in `src/index.css` for consistent theming.
- **Modules**: Component-specific styles in `Component.module.css`.
- **Icons**: Uses `lucide-react` or similar icon library.

## Integration

The frontend connects to the backend via:
- **HTTP API**: Fetching initial state and configuration.
- **WebSocket**: Real-time updates for agent messages, alerts, and trust scores.
