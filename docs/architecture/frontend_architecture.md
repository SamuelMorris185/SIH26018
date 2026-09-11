# Frontend Architecture — SIH26018

## 1. Frontend Technology Stack

- **Framework**: React 18+
- **Build Tool**: Vite
- **Language**: TypeScript 5+
- **Styling**: Vanilla CSS with modern CSS custom properties (variables), HSL color space, dark mode support, and glassmorphism UI tokens.
- **Icons**: Lucide React
- **API Client**: Fetch / Axios service wrapper

---

## 2. Directory Structure & Modular Layout

```
frontend/src/
├── assets/             # Static images, logos, vector icons
├── components/         # Reusable UI component hierarchy
│   ├── cards/          # HealthStatusCard, RecordSummaryCard, MetricCard
│   ├── common/         # Button, Badge, Input, Modal, Spinner
│   ├── feedback/       # AlertBanner, EmptyState, ProgressIndicator
│   ├── forms/          # DocumentUploadForm, RecordFilterForm
│   └── layout/         # Header, Sidebar, LayoutContainer, Footer
├── config/             # Application environment & API endpoint configuration
├── features/           # Feature-encapsulated modules
│   ├── digitization/   # Extraction review & confidence UI components
│   ├── land-records/   # Record tables, search, filters
│   └── validation/     # Audit log, validation flag review UI
├── hooks/              # Custom React hooks (useHealth, useRecords, useAsync)
├── pages/              # Top-level page views (Dashboard, RecordsPage, DigitizePage)
├── routes/             # App routing and page view dispatchers
├── services/           # API communication layer (apiClient, healthService, recordService)
├── types/              # Global TypeScript interfaces & API payload contracts
└── utils/              # Helper utilities (date formatting, status badges, validation helpers)
```

---

## 3. UI Component Layering & Design Tokens

### Design System Principles
1. **Curated Color Palette**: Modern dark mode backdrop (`#0d1117`), sleek card background (`#161b22`), high-contrast typography, and functional accent colors (Emerald green for validated records, Amber yellow for pending items, Rose red for validation errors).
2. **Micro-Interactions**: Smooth CSS transitions for button hovers, status badges, and loading states.
3. **No Unnecessary Dependencies**: Standard CSS design tokens allow zero-overhead, highly customizable styling.

---

## 4. API Communication & Service Layer

The frontend communicates with FastAPI exclusively through typed service wrappers located in `src/services/`.

```typescript
// Example Architecture Pattern for API Clients
import { apiClient } from './apiClient';
import { HealthStatus } from '../types';

export const healthService = {
  getHealth: async (): Promise<HealthStatus> => {
    return apiClient.get<HealthStatus>('/health');
  },
};
```

Features:
- Configurable base URL via `import.meta.env.VITE_API_BASE_URL`.
- Centralized error handling and standardized response normalization.
- Automatic fallback & diagnostic handling when backend is unreachable.
