import { ReactNode } from 'react';
import { TooltipProps } from 'recharts';
import { Card } from './card';

interface ChartConfig {
  [key: string]: {
    label: string;
    color: string;
  };
}

interface ChartContainerProps {
  children: ReactNode;
  config: ChartConfig;
  className?: string;
}

export function ChartContainer({ children, config, className }: ChartContainerProps) {
  return (
    <div className={className}>
      <div className="mb-4 flex items-center justify-between">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            {Object.entries(config).map(([key, value]) => (
              <div key={key} className="flex items-center space-x-2">
                <div
                  className="h-3 w-3 rounded-full"
                  style={{ backgroundColor: value.color }}
                />
                <span className="text-sm text-muted-foreground">
                  {value.label}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
      {children}
    </div>
  );
}

interface TooltipData {
  name: string;
  value: number;
  color: string;
  dataKey: string;
}

export function ChartTooltipContent({
  active,
  payload,
}: TooltipProps<number, string>) {
  if (!active || !payload) return null;

  return (
    <Card className="p-2 shadow-lg">
      {payload.map((entry, index) => {
        const data = entry as unknown as TooltipData;
        return (
          <div key={index} className="flex items-center space-x-2">
            <div
              className="h-2 w-2 rounded-full"
              style={{ backgroundColor: data.color || 'currentColor' }}
            />
            <span className="text-sm font-medium">
              {data.name}: {data.value || 0}
            </span>
          </div>
        );
      })}
    </Card>
  );
} 