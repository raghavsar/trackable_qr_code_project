# QR Code Project UI Design System

This document outlines the design system and UI language for the QR Code Project. It serves as a reference guide for maintaining visual consistency and implementing user interface components throughout the application.

## Design Principles

Our design system follows these core principles:

1. **Clarity**: UI elements should be clear and intuitive, supporting user goals without unnecessary complexity
2. **Consistency**: Visual elements, patterns, and interactions should be consistent across the application
3. **Hierarchy**: Important elements should stand out through visual weight, size, or positioning
4. **Feedback**: The system should provide clear feedback for user actions
5. **Accessibility**: Components should be accessible to all users, including those with disabilities

## Color Palette

### Primary Colors

- **Primary**: `#0284c7` - Primary brand color, used for primary buttons, links, and active states
- **Primary Hover**: `rgba(2, 132, 199, 0.9)` - Used for hover states of primary elements
- **Primary Light**: `rgba(2, 132, 199, 0.1)` - Used for backgrounds, borders of primary elements

### Neutral Colors

- **Background**: `#ffffff` - Main background color
- **Surface**: `#f8fafc` - Secondary background color for cards, containers
- **Border**: `#e2e8f0` - Standard border color
- **Muted**: `#94a3b8` - Subtle text and icons
- **Foreground**: `#0f172a` - Primary text color
- **Muted Foreground**: `#64748b` - Secondary text color

### Semantic Colors

- **Success**: `#10b981` - Success states, confirmations
- **Error**: `#ef4444` - Error states, destructive actions
- **Warning**: `#f59e0b` - Warning states, attention required
- **Info**: `#0ea5e9` - Information states, neutral guidance

## Typography

### Font Family

We use a system font stack to ensure optimal performance and native feel:

```css
font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
```

### Font Sizes

- **xs**: `0.75rem` (12px) - Very small text, footnotes
- **sm**: `0.875rem` (14px) - Secondary text, labels
- **base**: `1rem` (16px) - Body text, default size
- **lg**: `1.125rem` (18px) - Emphasized body text
- **xl**: `1.25rem` (20px) - Small headings
- **2xl**: `1.5rem` (24px) - Medium headings
- **3xl**: `1.875rem` (30px) - Large headings
- **4xl**: `2.25rem` (36px) - Extra large headings

### Font Weights

- **normal**: `400` - Regular text
- **medium**: `500` - Emphasized text
- **semibold**: `600` - Subtitles and secondary headings
- **bold**: `700` - Headings and important text

## Spacing

We use a consistent spacing scale:

- **px**: `1px` - Pixel-perfect adjustments
- **0.5**: `0.125rem` (2px) - Very small spacing
- **1**: `0.25rem` (4px) - Small spacing
- **1.5**: `0.375rem` (6px) - Small-medium spacing
- **2**: `0.5rem` (8px) - Medium-small spacing
- **3**: `0.75rem` (12px) - Medium spacing
- **4**: `1rem` (16px) - Default spacing
- **5**: `1.25rem` (20px) - Medium-large spacing
- **6**: `1.5rem` (24px) - Large spacing
- **8**: `2rem` (32px) - Extra large spacing
- **10**: `2.5rem` (40px) - Extra extra large spacing
- **12**: `3rem` (48px) - Huge spacing

## Shadow

- **sm**: `0 1px 2px 0 rgb(0 0 0 / 0.05)` - Subtle shadow
- **default**: `0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)` - Default shadow
- **md**: `0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)` - Medium shadow
- **lg**: `0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)` - Large shadow

## Border Radius

- **none**: `0px` - No border radius
- **sm**: `0.125rem` (2px) - Small border radius
- **default**: `0.25rem` (4px) - Default border radius
- **md**: `0.375rem` (6px) - Medium border radius
- **lg**: `0.5rem` (8px) - Large border radius
- **xl**: `0.75rem` (12px) - Extra large border radius
- **2xl**: `1rem` (16px) - Very large border radius
- **full**: `9999px` - Fully rounded (circles, pills)

## Components

### Cards

Cards are used to group related content and actions. They typically consist of:

- `Card`: The container component
- `CardHeader`: Contains title and optional description
- `CardTitle`: The card's title
- `CardDescription`: Additional supporting text
- `CardContent`: The main content area
- `CardFooter`: Optional footer area for actions

Example usage:

```tsx
<Card className="border shadow-sm">
  <CardHeader className="pb-4 border-b">
    <div className="flex justify-between items-center">
      <div>
        <CardTitle className="text-xl font-bold">Card Title</CardTitle>
        <CardDescription className="text-muted-foreground mt-1">
          Supporting description text
        </CardDescription>
      </div>
      <Badge variant="outline">Optional Badge</Badge>
    </div>
  </CardHeader>
  <CardContent className="p-6">
    {/* Card content goes here */}
  </CardContent>
</Card>
```

### Buttons

Buttons communicate actions users can take and are used for:

- Form submissions
- Modal triggers
- Interactive actions

Variants:
- `default`: Primary action buttons
- `secondary`: Secondary action buttons
- `outline`: Subtle, less emphasized actions
- `ghost`: Very subtle buttons, often used in toolbars
- `destructive`: Indicates a destructive action (delete, remove)
- `link`: Appears as a link but behaves like a button

Example usage:

```tsx
<Button variant="default">Primary Action</Button>
<Button variant="outline">Secondary Action</Button>
<Button variant="destructive">Delete</Button>
<Button disabled>Disabled</Button>
<Button size="sm">Small</Button>
<Button size="lg">Large</Button>
<Button className="gap-2">
  <PlusIcon className="h-4 w-4" />
  With Icon
</Button>
```

### Tabs

Tabs organize content into different sections, displaying one section at a time:

- `Tabs`: Container for the entire tabs component
- `TabsList`: Container for the tab triggers
- `TabsTrigger`: The clickable tab buttons
- `TabsContent`: The content associated with each tab

Example usage:

```tsx
<Tabs defaultValue="tab1" className="w-full">
  <TabsList className="grid grid-cols-3">
    <TabsTrigger value="tab1" className="gap-2">
      <Icon1 className="h-4 w-4" />
      First Tab
    </TabsTrigger>
    <TabsTrigger value="tab2" className="gap-2">
      <Icon2 className="h-4 w-4" />
      Second Tab
    </TabsTrigger>
    <TabsTrigger value="tab3" className="gap-2">
      <Icon3 className="h-4 w-4" />
      Third Tab
    </TabsTrigger>
  </TabsList>
  <TabsContent value="tab1">
    Content for first tab
  </TabsContent>
  <TabsContent value="tab2">
    Content for second tab
  </TabsContent>
  <TabsContent value="tab3">
    Content for third tab
  </TabsContent>
</Tabs>
```

### Badges

Badges highlight status, counts, or categories:

- `default`: Standard badge
- `secondary`: Less prominent badge
- `outline`: Badge with only a border
- `destructive`: Indicates a negative or critical status

Example usage:

```tsx
<Badge>Default</Badge>
<Badge variant="secondary">Secondary</Badge>
<Badge variant="outline">Outline</Badge>
<Badge variant="destructive">Destructive</Badge>

<!-- With icon -->
<Badge variant="outline" className="gap-1">
  <CheckCircle2 className="h-3.5 w-3.5" />
  Verified
</Badge>
```

### Inputs and Forms

Form elements collect user data:

- `Input`: Text inputs for single-line text
- `Textarea`: Multi-line text inputs
- `Label`: Form field labels
- `Select`: Dropdown selection inputs

Example usage:

```tsx
<div className="space-y-1.5">
  <Label htmlFor="name" className="text-sm font-medium">
    <User className="h-3.5 w-3.5 inline mr-1.5" />
    Name
  </Label>
  <Input
    id="name"
    name="name"
    placeholder="Enter your name"
    className="border-muted-foreground/20"
  />
</div>

<div className="space-y-1.5">
  <Label htmlFor="description" className="text-sm font-medium">
    <FileText className="h-3.5 w-3.5 inline mr-1.5" />
    Description
  </Label>
  <Textarea
    id="description"
    name="description"
    placeholder="Enter a description"
    className="h-24 resize-none border-muted-foreground/20"
  />
</div>
```

### Dialogs and Modals

Dialogs present temporary content that requires user attention or interaction:

- `Dialog`: Container component
- `DialogTrigger`: Element that opens the dialog
- `DialogContent`: The dialog's content
- `DialogHeader`: Header section with title and description
- `DialogTitle`: Dialog title
- `DialogDescription`: Supporting text
- `DialogFooter`: Optional footer area for actions
- `DialogClose`: Button to close the dialog

Example usage:

```tsx
<Dialog>
  <DialogTrigger asChild>
    <Button variant="outline">Open Dialog</Button>
  </DialogTrigger>
  <DialogContent className="sm:max-w-[425px]">
    <DialogHeader>
      <DialogTitle>Dialog Title</DialogTitle>
      <DialogDescription>
        This dialog is used for important interactions.
      </DialogDescription>
    </DialogHeader>
    <div className="py-4">
      {/* Dialog content goes here */}
    </div>
    <DialogFooter>
      <Button type="submit">Confirm</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

## Layout Patterns

### Container

Use the container class for consistent width and centering:

```tsx
<div className="container mx-auto px-4 max-w-7xl">
  {/* Content */}
</div>
```

### Grids

For responsive layouts:

```tsx
<div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
  {/* Grid items */}
</div>
```

### Card Layouts

For card-based interfaces:

```tsx
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
  {/* Cards */}
</div>
```

### Form Layouts

Standard form structure:

```tsx
<form className="space-y-6">
  <div className="space-y-4">
    {/* Form fields */}
  </div>
  <div className="flex justify-end space-x-2">
    <Button variant="outline">Cancel</Button>
    <Button type="submit">Submit</Button>
  </div>
</form>
```

## Common UI Patterns

### Metric Cards

For displaying key statistics:

```tsx
<div className="grid grid-cols-1 md:grid-cols-4 gap-4">
  <Card>
    <CardContent className="p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-muted-foreground">Total Scans</p>
          <h3 className="text-2xl font-bold mt-1">2,543</h3>
        </div>
        <div className="p-2 bg-primary/10 rounded-full">
          <BarChartIcon className="h-5 w-5 text-primary" />
        </div>
      </div>
    </CardContent>
  </Card>
  {/* More metric cards */}
</div>
```

### Data Tables

For displaying structured data:

```tsx
<div className="rounded-md border">
  <table className="min-w-full divide-y divide-border">
    <thead className="bg-muted/50">
      <tr>
        <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Name</th>
        <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Date</th>
        <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Status</th>
      </tr>
    </thead>
    <tbody className="bg-white divide-y divide-border">
      {/* Table rows */}
    </tbody>
  </table>
</div>
```

### Empty States

For when there's no data to display:

```tsx
<div className="flex flex-col items-center justify-center h-60 text-center p-6">
  <div className="p-3 bg-muted/30 rounded-full mb-4">
    <InboxIcon className="h-6 w-6 text-muted-foreground" />
  </div>
  <h3 className="text-lg font-medium">No data found</h3>
  <p className="text-sm text-muted-foreground mt-1 max-w-sm">
    There's no data to display right now. Try adjusting your filters or create your first item.
  </p>
  <Button className="mt-4">Create Item</Button>
</div>
```

### Activity Feeds

For displaying user activity:

```tsx
<div className="space-y-4">
  <div className="flex items-start gap-4">
    <div className="p-2 bg-blue-50 rounded-full">
      <Icon className="h-4 w-4 text-blue-500" />
    </div>
    <div>
      <p className="text-sm font-medium">Activity title</p>
      <p className="text-xs text-muted-foreground">Details about the activity</p>
      <p className="text-xs text-muted-foreground mt-1">2 hours ago</p>
    </div>
  </div>
  {/* More activity items */}
</div>
```

## Best Practices

1. **Component Consistency**: Use the established components consistently throughout the application.
2. **Responsive Design**: Ensure all interfaces are responsive and work well on all screen sizes.
3. **Visual Hierarchy**: Establish clear importance through size, weight, and color.
4. **Error States**: Provide clear error messages and visual cues when errors occur.
5. **Loading States**: Use skeleton loaders or spinners to indicate loading content.
6. **Empty States**: Design helpful empty states with clear actions for users.
7. **Icons**: Use icons consistently and pair them with text for clarity.
8. **Color Usage**: Follow the color system and ensure sufficient contrast.
9. **Spacing**: Maintain consistent spacing using the spacing scale.
10. **Typography**: Follow the type scale and limit the variety of text styles.

## Examples and Implementation Notes

### Analytics Dashboard

Our analytics dashboard showcases several UI patterns:

1. **Tabbed Interface**: Using `Tabs` component to organize different data views
2. **Metric Cards**: Displaying key statistics at the top of the dashboard
3. **Data Visualization**: Using charts with consistent styling
4. **Activity Feed**: Showing recent activity in a scrollable area
5. **Empty States**: Providing helpful messages when no data is available

### QR Code Creation Form

The QR code creation form demonstrates:

1. **Multi-step Form**: Using tabs to organize form sections
2. **Form Validation**: Highlighting required fields and showing appropriate errors
3. **File Upload**: Implementing image upload with preview
4. **Form Layout**: Using consistent spacing and field grouping
5. **Action Buttons**: Placing primary actions in prominent positions

## Accessibility Guidelines

1. **Color Contrast**: Ensure text has sufficient contrast against its background
2. **Keyboard Navigation**: All interactive elements should be keyboard accessible
3. **Focus States**: Provide visible focus indicators for keyboard navigation
4. **Screen Readers**: Include appropriate ARIA attributes when needed
5. **Text Alternatives**: Provide alt text for images and icons
6. **Form Labels**: All form controls should have associated labels
7. **Error Handling**: Errors should be clearly identified and described

## Conclusion

This design system provides a foundation for building consistent, accessible, and user-friendly interfaces for the QR Code Project. By adhering to these guidelines, we can maintain a cohesive user experience across the entire application.

For questions or suggestions regarding the design system, please contact the UI design team.