# Content Display Components

Flexible content display components for the OHDSI Dashboard that support multi-source content (PubMed, YouTube, GitHub, Discourse, Wiki) in both list and grid layouts.

## Components

### ContentCard
Enhanced content card component that displays content from multiple sources with source-specific layouts and features. Supports Schema v3 structure.

**Features:**
- Source-specific styling and metadata
- AI enhancement indicators
- Hover states and animations  
- Responsive design
- Accessibility compliant

### ContentList
Unified list view component with advanced features for displaying collections of content items.

**Features:**
- Three view modes: compact, expanded, grouped
- Source-based grouping with collapsible sections
- Bulk selection with checkboxes
- Virtual scrolling for performance (50+ items)
- Multiple sort options (relevance, date, popularity, score, title)
- Loading states with skeletons
- Error states with retry functionality
- Empty state handling

**Props:**
```typescript
interface ContentListProps {
  items: ContentItem[]
  viewMode?: 'compact' | 'expanded' | 'grouped'
  sortBy?: SortOption
  onItemClick?: (item: ContentItem) => void
  onItemSelect?: (ids: string[]) => void
  selectedIds?: string[]
  enableBulkActions?: boolean
  loading?: boolean
  error?: Error
  emptyMessage?: string
  onSortChange?: (sort: SortOption) => void
  onViewModeChange?: (mode: ViewMode) => void
  onRetry?: () => void
  enableVirtualScrolling?: boolean
  className?: string
}
```

### ContentGrid
Masonry layout grid component optimized for mixed content heights and responsive design.

**Features:**
- True masonry layout for optimal space usage
- Source-specific card sizing (videos larger, repos compact)
- Responsive column count (1-4 columns based on screen size)
- Lazy loading with intersection observer
- Hover previews for media content (YouTube videos)
- Smooth animations and transitions
- CSS containment for performance
- Filter animations

**Props:**
```typescript
interface ContentGridProps {
  items: ContentItem[]
  columns?: number | 'auto'
  gap?: number
  onItemClick?: (item: ContentItem) => void
  loading?: boolean
  error?: Error
  emptyMessage?: string
  animateOnFilter?: boolean
  enableLazyLoading?: boolean
  enableHoverPreviews?: boolean
  onRetry?: () => void
  className?: string
}
```

## Type Definitions

### ContentItem
Core content interface aligned with Schema v3:

```typescript
interface ContentItem {
  id: string
  title: string
  description?: string
  abstract?: string
  content_type: string
  source: 'pubmed' | 'youtube' | 'github' | 'discourse' | 'wiki'
  
  // Schema v3 fields
  categories: string[]
  final_score?: number  // replaces combined_score
  metrics: ContentMetrics
  ai_enhanced?: boolean
  ai_confidence?: number  // replaces ai_quality_score
  
  // Source-specific fields
  // ... (see types/content.ts for full definition)
}
```

## Performance Features

### Optimization Techniques
- **React.memo**: All components memoized for efficient re-renders
- **Virtual Scrolling**: Automatically enabled for lists with 50+ items
- **Lazy Loading**: Images and off-screen content loaded on demand
- **CSS Containment**: Layout, style, and paint containment for better performance
- **Smooth Animations**: 60fps animations with hardware acceleration

### Performance Targets
- **Load Time**: <300ms for initial render
- **Scroll Performance**: 60fps scrolling with virtual scrolling
- **Memory Usage**: Efficient cleanup and garbage collection
- **Bundle Size**: Minimal impact on overall bundle size

## Usage Examples

### Basic List View
```tsx
import { ContentList } from '@/components/content/content-list'

<ContentList
  items={contentItems}
  viewMode="compact"
  onItemClick={(item) => navigate(`/content/${item.id}`)}
  enableBulkActions={true}
  onItemSelect={setSelectedItems}
/>
```

### Masonry Grid View
```tsx
import { ContentGrid } from '@/components/content/content-grid'

<ContentGrid
  items={contentItems}
  columns="auto"
  onItemClick={(item) => navigate(`/content/${item.id}`)}
  enableHoverPreviews={true}
  animateOnFilter={true}
/>
```

### With Loading States
```tsx
<ContentList
  items={items}
  loading={isLoading}
  error={error}
  onRetry={refetch}
  emptyMessage="No content matches your search criteria."
/>
```

## Integration with Existing Components

These components work seamlessly with:
- **ContentCard**: Used internally for individual item display
- **Design System**: Consistent with existing UI components
- **Search**: Compatible with search highlighting
- **Filters**: Supports filtered item arrays
- **Mobile**: Fully responsive across all device sizes

## Accessibility Features

- **Keyboard Navigation**: Full keyboard support
- **Screen Readers**: Proper ARIA labels and descriptions
- **Focus Management**: Logical focus order and visible focus indicators
- **Color Contrast**: WCAG AA compliant color combinations
- **Reduced Motion**: Respects user's motion preferences

## Browser Support

- Chrome 88+
- Firefox 85+
- Safari 14+
- Edge 88+