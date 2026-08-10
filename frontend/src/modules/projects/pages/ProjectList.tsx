import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as zod from "zod";
import { toast } from "sonner";
import {
  FolderKanban,
  Plus,
  Search,
  Pencil,
  Trash2,
  ExternalLink,
  Loader2,
  Calendar,
  Layers,
} from "lucide-react";

import {
  useProjectsQuery,
  useCreateProjectMutation,
  useUpdateProjectMutation,
  useDeleteProjectMutation,
} from "../hooks/useProjects";
import { Project } from "../types";
import { SidebarLayout } from "@/shared/layouts/SidebarLayout";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

// Form validation schema
const projectSchema = zod.object({
  name: zod.string().min(2, "Project name must be at least 2 characters").max(150),
  description: zod.string().max(1000).optional(),
});

type ProjectFormValues = zod.infer<typeof projectSchema>;

export const ProjectList: React.FC = () => {
  const navigate = useNavigate();
  const { data: projects, isLoading, isError, refetch } = useProjectsQuery();
  const createMutation = useCreateProjectMutation();
  const updateMutation = useUpdateProjectMutation();
  const deleteMutation = useDeleteProjectMutation();

  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [deletingProjectId, setDeletingProjectId] = useState<string | null>(null);

  // Debounce search input
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(search);
    }, 300);
    return () => clearTimeout(handler);
  }, [search]);

  // Form setup
  const {
    register,
    handleSubmit,
    reset,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<ProjectFormValues>({
    resolver: zodResolver(projectSchema),
  });

  // Prepopulate edit form
  useEffect(() => {
    if (editingProject) {
      setValue("name", editingProject.name);
      setValue("description", editingProject.description || "");
    } else {
      reset();
    }
  }, [editingProject, setValue, reset]);

  const onCreateSubmit = async (values: ProjectFormValues) => {
    try {
      await createMutation.mutateAsync(values);
      toast.success("Project Created Successfully");
      setIsCreateOpen(false);
      reset();
    } catch (err: any) {
      toast.error(err.message || "Failed to create project");
    }
  };

  const onEditSubmit = async (values: ProjectFormValues) => {
    if (!editingProject) return;
    try {
      await updateMutation.mutateAsync({
        projectId: editingProject.id,
        data: {
          name: values.name,
          description: values.description,
        },
      });
      toast.success("Project Updated Successfully");
      setEditingProject(null);
    } catch (err: any) {
      toast.error(err.message || "Failed to update project");
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deletingProjectId) return;
    try {
      await deleteMutation.mutateAsync(deletingProjectId);
      toast.success("Project Deleted Successfully");
      setDeletingProjectId(null);
    } catch (err: any) {
      toast.error(err.message || "Failed to delete project");
    }
  };

  // Filter projects by debounced search
  const filteredProjects = projects?.filter((project) =>
    project.name.toLowerCase().includes(debouncedSearch.toLowerCase())
  );

  return (
    <SidebarLayout>
      <div className="space-y-6">
        {/* Header Section */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Projects Workspace</h1>
            <p className="text-sm text-muted-foreground">Select a project context or create a new workspace repository.</p>
          </div>
          <Button onClick={() => setIsCreateOpen(true)} className="sm:w-fit w-full">
            <Plus className="w-4 h-4 mr-2" />
            Create Project
          </Button>
        </div>

        {/* Search Bar */}
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search projects by name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10 max-w-md w-full bg-card/40 border-border"
          />
        </div>

        {/* Loading Skeletons */}
        {isLoading && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <Card key={i} className="bg-card/45 border-border">
                <CardHeader className="space-y-2">
                  <Skeleton className="h-6 w-3/4 bg-muted/40" />
                  <Skeleton className="h-4 w-1/2 bg-muted/40" />
                </CardHeader>
                <CardContent className="space-y-2">
                  <Skeleton className="h-4 w-full bg-muted/40" />
                  <Skeleton className="h-4 w-5/6 bg-muted/40" />
                </CardContent>
                <CardFooter className="flex justify-end gap-2 border-t border-border pt-4 mt-2">
                  <Skeleton className="h-8 w-20 bg-muted/40" />
                  <Skeleton className="h-8 w-8 bg-muted/40 animate-pulse" />
                </CardFooter>
              </Card>
            ))}
          </div>
        )}

        {/* Error States */}
        {isError && (
          <Card className="max-w-md mx-auto p-6 text-center border-destructive/20 bg-destructive/5">
            <h2 className="text-sm font-semibold text-destructive">Connection Failure</h2>
            <p className="text-xs text-muted-foreground mt-2">Could not acquire workspace configurations from the database.</p>
            <Button onClick={() => refetch()} variant="outline" className="mt-4 text-xs font-semibold">
              Retry Connection
            </Button>
          </Card>
        )}

        {/* Empty State */}
        {!isLoading && !isError && (!filteredProjects || filteredProjects.length === 0) && (
          <Card className="max-w-lg mx-auto py-12 px-6 border-dashed border-2 border-border bg-card/20 text-center flex flex-col items-center justify-center">
            <div className="w-12 h-12 flex items-center justify-center bg-primary/10 rounded-full text-primary mb-4">
              <FolderKanban className="w-6 h-6" />
            </div>
            <CardTitle className="text-md font-semibold">No Workspace Active</CardTitle>
            <CardDescription className="text-xs text-muted-foreground mt-2 max-w-sm">
              You must create or join a project context before analyzing medical claims or structured reports.
            </CardDescription>
            <Button onClick={() => setIsCreateOpen(true)} className="mt-6">
              <Plus className="w-4 h-4 mr-2" />
              Create First Project
            </Button>
          </Card>
        )}

        {/* Projects Cards Grid */}
        {!isLoading && !isError && filteredProjects && filteredProjects.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredProjects.map((project) => (
              <Card key={project.id} className="bg-card/50 backdrop-blur-xl border-border hover:shadow-lg transition-all duration-300 flex flex-col group">
                <CardHeader>
                  <CardTitle className="text-md font-semibold text-foreground group-hover:text-primary transition-colors truncate">
                    {project.name}
                  </CardTitle>
                  <CardDescription className="flex items-center gap-1.5 text-xs text-muted-foreground mt-1">
                    <Calendar className="w-3.5 h-3.5" />
                    <span>Created: {new Date(project.created_at).toLocaleDateString()}</span>
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex-1 min-h-[4rem]">
                  <p className="text-xs text-muted-foreground line-clamp-3">
                    {project.description || "No project description provided."}
                  </p>
                </CardContent>
                <CardFooter className="flex items-center justify-between border-t border-border/65 pt-4 mt-4 bg-muted/10">
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="w-8 h-8 rounded-full text-muted-foreground hover:text-foreground hover:bg-muted"
                      onClick={() => setEditingProject(project)}
                    >
                      <Pencil className="w-3.5 h-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="w-8 h-8 rounded-full text-red-500 hover:text-red-600 hover:bg-red-50/10"
                      onClick={() => setDeletingProjectId(project.id)}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      localStorage.setItem("activeProjectId", project.id);
                      localStorage.setItem("activeProjectName", project.name);
                      navigate(`/projects/${project.id}`);
                    }}
                  >
                    <ExternalLink className="w-3.5 h-3.5 mr-2" />
                    Open Project
                  </Button>

                </CardFooter>
              </Card>
            ))}
          </div>
        )}

        {/* Create Project Modal */}
        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogContent className="bg-card border-border sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle className="text-md font-semibold text-foreground">Create Project</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit(onCreateSubmit)} className="space-y-4 pt-2">
              <div className="space-y-1">
                <Label htmlFor="name" className="text-xs">Project Name *</Label>
                <Input
                  id="name"
                  placeholder="e.g. Clinical Claims Audit 2026"
                  {...register("name")}
                  className="bg-card border-border"
                />
                {errors.name && <p className="text-[10px] text-destructive">{errors.name.message}</p>}
              </div>

              <div className="space-y-1">
                <Label htmlFor="description" className="text-xs">Description</Label>
                <Textarea
                  id="description"
                  placeholder="Optional details outlining analysis goals, team boundaries..."
                  {...register("description")}
                  className="bg-card border-border min-h-[100px]"
                />
                {errors.description && <p className="text-[10px] text-destructive">{errors.description.message}</p>}
              </div>

              <DialogFooter className="pt-2">
                <Button type="button" variant="outline" onClick={() => setIsCreateOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  Create
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Edit Project Modal */}
        <Dialog open={!!editingProject} onOpenChange={(open) => !open && setEditingProject(null)}>
          <DialogContent className="bg-card border-border sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle className="text-md font-semibold text-foreground">Edit Project Details</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit(onEditSubmit)} className="space-y-4 pt-2">
              <div className="space-y-1">
                <Label htmlFor="edit-name" className="text-xs">Project Name *</Label>
                <Input
                  id="edit-name"
                  placeholder="e.g. Clinical Claims Audit 2026"
                  {...register("name")}
                  className="bg-card border-border"
                />
                {errors.name && <p className="text-[10px] text-destructive">{errors.name.message}</p>}
              </div>

              <div className="space-y-1">
                <Label htmlFor="edit-description" className="text-xs">Description</Label>
                <Textarea
                  id="edit-description"
                  placeholder="Optional details..."
                  {...register("description")}
                  className="bg-card border-border min-h-[100px]"
                />
                {errors.description && <p className="text-[10px] text-destructive">{errors.description.message}</p>}
              </div>

              <DialogFooter className="pt-2">
                <Button type="button" variant="outline" onClick={() => setEditingProject(null)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  Save Changes
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation Alert */}
        <AlertDialog open={!!deletingProjectId} onOpenChange={(open) => !open && setDeletingProjectId(null)}>
          <AlertDialogContent className="bg-card border-border">
            <AlertDialogHeader>
              <AlertDialogTitle className="text-md font-semibold">Delete Project Context?</AlertDialogTitle>
              <AlertDialogDescription className="text-xs text-muted-foreground">
                This action is a soft-delete operation. You can recover this project repository later through backend metadata administration.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={handleDeleteConfirm} className="bg-red-600 hover:bg-red-700 text-white">
                Delete
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </SidebarLayout>
  );
};
export default ProjectList;
