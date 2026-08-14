import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { ThemeProvider } from "next-themes";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { lazy, Suspense } from "react";
import { AuthProvider } from "./contexts/AuthContext";
import { AnimationProvider } from "./components/animations/AnimationProvider";

const Index = lazy(() => import("./pages/Index"));
const NotFound = lazy(() => import("./pages/NotFound"));
const Login = lazy(() => import("./pages/Login"));
const Register = lazy(() => import("./pages/Register"));
const MyDocuments = lazy(() => import("./pages/MyDocuments"));
const ViewDocument = lazy(() => import("./pages/ViewDocument"));
const Profile = lazy(() => import("./pages/Profile"));
const Settings = lazy(() => import("./pages/Settings"));
const Assistant = lazy(() => import("./pages/Assistant"));
const ProjectList = lazy(() => import("./modules/projects/pages/ProjectList"));
const ProjectDetail = lazy(() => import("./modules/projects/pages/ProjectDetail"));
const Knowledge = lazy(() => import("./pages/Knowledge"));

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <AnimationProvider>
          <Toaster />
          <Sonner />
        <AuthProvider>
          <BrowserRouter>
            <Suspense fallback={
              <div className="h-screen w-screen flex flex-col items-center justify-center bg-background text-muted-foreground font-medium">
                <img src="/favicon1.png" alt="Loading DocLens..." className="w-16 h-16 animate-spin mb-4" />
                <p className="text-sm">Loading DocLens...</p>
              </div>
            }>
              <Routes>
                <Route path="/" element={<Index />} />
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />
                <Route path="/profile" element={<Profile />} />
                <Route path="/settings" element={<Settings />} />
                <Route path="/knowledge" element={<Knowledge />} />
                <Route path="/projects" element={<ProjectList />} />
                <Route path="/projects/:projectId" element={<ProjectDetail />} />
                <Route path="/projects/:projectId/workspace" element={<Assistant />} />
                <Route path="/documents/:documentId/workspace" element={<Assistant />} />
                <Route path="/assistant" element={<Assistant />} />
                <Route path="/my-documents" element={<MyDocuments />} />
                <Route path="/documents/:id" element={<ViewDocument />} />
                <Route path="*" element={<NotFound />} />
              </Routes>
            </Suspense>
          </BrowserRouter>
        </AuthProvider>
      </AnimationProvider>
    </ThemeProvider>
  </QueryClientProvider>
);

export default App;
