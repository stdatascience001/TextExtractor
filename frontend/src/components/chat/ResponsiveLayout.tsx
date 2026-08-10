import React, { useState, useEffect } from 'react';
import { useIsMobile } from '@/hooks/use-mobile';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Menu, X, FileText } from 'lucide-react';
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable';

interface ResponsiveLayoutProps {
  sidebar: React.ReactNode;
  main: React.ReactNode;
  rightPanel: React.ReactNode;
}

export function ResponsiveLayout({ sidebar, main, rightPanel }: ResponsiveLayoutProps) {
  const isMobile = useIsMobile();
  const [isTablet, setIsTablet] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [rightPanelOpen, setRightPanelOpen] = useState(false);

  useEffect(() => {
    const checkTablet = () => {
      setIsTablet(window.innerWidth <= 1024 && window.innerWidth > 768);
    };

    checkTablet();
    window.addEventListener('resize', checkTablet);
    return () => window.removeEventListener('resize', checkTablet);
  }, []);

  // Mobile layout - use sheets/drawers
  if (isMobile) {
    return (
      <div className="h-screen flex flex-col">
        {/* Mobile Header */}
        <div className="flex items-center justify-between p-4 border-b border-border bg-background">
          <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="sm">
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-80 p-0">
              {sidebar}
            </SheetContent>
          </Sheet>

          <h1 className="text-lg font-semibold">Document Chat</h1>

          <Sheet open={rightPanelOpen} onOpenChange={setRightPanelOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="sm">
                <FileText className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="w-full p-0">
              {rightPanel}
            </SheetContent>
          </Sheet>
        </div>

        {/* Main Content */}
        <div className="flex-1 overflow-hidden">
          {main}
        </div>
      </div>
    );
  }

  // Tablet layout - collapsible panels
  if (isTablet) {
    return (
      <ResizablePanelGroup direction="horizontal" className="h-screen overflow-hidden p-3 gap-3 bg-slate-50">
        <ResizablePanel defaultSize={25} minSize={20} maxSize={35}>
          <div className="h-full overflow-hidden flex flex-col border border-border rounded-2xl bg-card shadow-sm">
            {sidebar}
          </div>
        </ResizablePanel>

        <ResizableHandle className="w-1 bg-transparent hover:bg-primary/20 transition-colors" />

        <ResizablePanel defaultSize={50} minSize={40}>
          <div className="h-full overflow-hidden flex flex-col border border-border rounded-2xl bg-card shadow-sm">
            {main}
          </div>
        </ResizablePanel>

        <ResizableHandle className="w-1 bg-transparent hover:bg-primary/20 transition-colors" />

        <ResizablePanel defaultSize={25} minSize={20} maxSize={35}>
          <div className="h-full overflow-hidden flex flex-col border border-border rounded-2xl bg-card shadow-sm">
            {rightPanel}
          </div>
        </ResizablePanel>
      </ResizablePanelGroup>
    );
  }

  // Desktop layout - full resizable panels
  return (
    <ResizablePanelGroup direction="horizontal" className="h-screen overflow-hidden p-3 gap-3 bg-slate-50">
      <ResizablePanel defaultSize={20} minSize={15} maxSize={30}>
        <div className="h-full overflow-hidden flex flex-col border border-border rounded-2xl bg-card shadow-sm">
          {sidebar}
        </div>
      </ResizablePanel>

      <ResizableHandle className="w-1 bg-transparent hover:bg-primary/20 transition-colors" />

      <ResizablePanel defaultSize={50} minSize={30}>
        <div className="h-full overflow-hidden flex flex-col border border-border rounded-2xl bg-card shadow-sm">
          {main}
        </div>
      </ResizablePanel>

      <ResizableHandle className="w-1 bg-transparent hover:bg-primary/20 transition-colors" />

      <ResizablePanel defaultSize={30} minSize={20} maxSize={50}>
        <div className="h-full overflow-hidden flex flex-col border border-border rounded-2xl bg-card shadow-sm">
          {rightPanel}
        </div>
      </ResizablePanel>
    </ResizablePanelGroup>
  );
}