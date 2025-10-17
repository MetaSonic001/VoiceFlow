# VoiceFlow AI Platform - Frontend

A modern, comprehensive AI agent platform built with Next.js 15, featuring advanced dashboard management, real-time analytics, and enterprise-grade features.

## 🚀 Features

### Core Functionality
- **AI Agent Management** - Create, configure, and deploy intelligent voice and chat agents
- **Real-time Analytics** - Comprehensive dashboards with usage metrics and performance insights
- **Multi-tenant Architecture** - Secure isolation between organizations and users
- **Voice & Chat Integration** - Seamless Twilio integration for voice calls and messaging

### Enterprise Dashboard Features
- **Audit Logs** - Complete audit trail of all user actions and system events
- **Notifications System** - Real-time alerts and message center with delivery preferences
- **Backup & Restore** - Automated data backup with full/incremental/configuration options
- **Billing & Usage** - Detailed usage tracking, cost analysis, and subscription management
- **Integrations Hub** - Connect third-party services (Twilio, OpenAI, Stripe, Slack, etc.)
- **Team Management** - User roles, permissions, and collaboration tools
- **System Health Monitoring** - Real-time system status and performance metrics
- **Reports & Analytics** - Custom report generation and data export
- **API Documentation** - Interactive API docs with testing capabilities

### Technical Features
- **Modern UI/UX** - Built with Tailwind CSS, Radix UI, and Framer Motion
- **Authentication** - Clerk-based authentication with role-based access
- **Real-time Updates** - WebSocket connections for live data
- **Responsive Design** - Mobile-first approach with adaptive layouts
- **Type Safety** - Full TypeScript implementation
- **Performance Optimized** - Code splitting, lazy loading, and caching

## 🏗️ Architecture

```
Frontend (Next.js 15)          Backend Services
├── Dashboard Pages            ├── Express.js API (Port 3001)
├── Authentication (Clerk)     ├── FastAPI Ingestion (Port 8001)
├── Real-time Updates          ├── PostgreSQL Database
├── File Uploads               ├── Redis Cache
└── Third-party Integrations   ├── MinIO Storage
                                ├── ChromaDB Vector Store
                                └── External APIs (Twilio, OpenAI, etc.)
```

## 📋 Prerequisites

- Node.js 18+ and npm
- Backend services running (see backend README)
- PostgreSQL database
- Redis instance
- MinIO or S3-compatible storage

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd voiceflow-ai-platform
npm install
```

### 2. Environment Configuration
```bash
cp .env.example .env.local
```

Edit `.env.local` with your configuration:
```env
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:3001

# Frontend Base URL
NEXT_PUBLIC_PUBLIC_BASE_URL=http://localhost:3000

# Clerk Authentication (if using)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=your_clerk_key
CLERK_SECRET_KEY=your_clerk_secret

# Optional: Analytics and Monitoring
NEXT_PUBLIC_ANALYTICS_ID=your_analytics_id
```

### 3. Development Server
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### 4. Production Build
```bash
npm run build
npm start
```

## 📁 Project Structure

```
voiceflow-ai-platform/
├── app/                          # Next.js App Router
│   ├── dashboard/               # Dashboard pages
│   │   ├── audit/              # Audit logs
│   │   ├── backup/             # Backup & restore
│   │   ├── billing/            # Billing & usage
│   │   ├── integrations/       # Third-party integrations
│   │   ├── notifications/      # Notification center
│   │   └── ...                 # Other dashboard pages
│   ├── globals.css             # Global styles
│   └── layout.tsx              # Root layout
├── components/                  # Reusable components
│   ├── dashboard/              # Dashboard-specific components
│   ├── ui/                     # UI components (Radix/Shadcn)
│   └── ...                     # Other components
├── lib/                        # Utilities and configurations
│   ├── api-client.ts           # Backend API client
│   └── ...                     # Other utilities
└── public/                     # Static assets
```

## 🔧 Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript type checking

## 🔐 Authentication

The platform uses Clerk for authentication with the following features:
- User registration and login
- Social login (Google, GitHub, etc.)
- Role-based access control
- Session management
- User profile management

## 📊 Dashboard Features

### Agent Management
- Create and configure AI agents
- Voice and chat personality settings
- Knowledge base integration
- Channel setup (Twilio, web chat, etc.)
- Performance monitoring

### Analytics & Reporting
- Real-time usage metrics
- Call logs and conversation analytics
- Performance dashboards
- Custom report generation
- Data export capabilities

### System Administration
- User and team management
- System health monitoring
- Backup and restore operations
- Integration management
- Audit logging

## 🔗 API Integration

The frontend communicates with multiple backend services:

- **Main API** (Port 3001): User management, agent configuration, analytics
- **Ingestion Service** (Port 8001): Document processing and vector embeddings
- **External APIs**: Twilio, OpenAI, Stripe, and other integrations

## 🎨 UI/UX Design

- **Modern Design System**: Consistent color palette and typography
- **Responsive Layout**: Mobile-first approach with adaptive components
- **Accessibility**: WCAG compliant with keyboard navigation
- **Dark/Light Mode**: Automatic theme switching
- **Smooth Animations**: Framer Motion for enhanced user experience

## 🧪 Testing

```bash
# Run tests
npm run test

# Run tests with coverage
npm run test:coverage

# Run e2e tests
npm run test:e2e
```

## 📚 Documentation

- [API Documentation](./docs/api.md)
- [Deployment Guide](./docs/deployment.md)
- [Contributing Guidelines](./docs/contributing.md)
- [Troubleshooting](./docs/troubleshooting.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [docs.voiceflow.ai](https://docs.voiceflow.ai)
- **Issues**: [GitHub Issues](https://github.com/your-org/voiceflow/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/voiceflow/discussions)

## 🔄 Recent Updates

- ✅ Complete dashboard redesign with enterprise features
- ✅ Real-time notifications and audit logging
- ✅ Backup/restore functionality with scheduling
- ✅ Billing and usage tracking
- ✅ Third-party integrations hub
- ✅ Improved authentication and user management
- ✅ Enhanced API documentation
- ✅ Mobile-responsive design improvements
