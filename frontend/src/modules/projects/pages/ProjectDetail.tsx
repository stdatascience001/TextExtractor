import React, { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as zod from "zod";
import { toast } from "sonner";
import {
  ArrowLeft,
  UserPlus,
  Shield,
  Loader2,
  Trash2,
  MoreVertical,
  CheckCircle,
  FileUp,
  UserCheck,
} from "lucide-react";

import { useAuth } from "@/contexts/AuthContext";
import {
  useProjectQuery,
  useAddMemberMutation,
  useUpdateMemberMutation,
  useRemoveMemberMutation,
} from "../hooks/useProjects";
import { ProjectRole, Member } from "../types";
import { SidebarLayout } from "@/shared/layouts/SidebarLayout";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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

// Form validation schema for adding members
const memberSchema = zod.object({
  email: zod.string().email("Please enter a valid email address"),
  role: zod.enum(["owner", "admin", "reviewer", "viewer"]),
});

type MemberFormValues = zod.infer<typeof memberSchema>;

export const ProjectDetail: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { user: currentUser } = useAuth();

  const { data: projectDetail, isLoading, isError, refetch } = useProjectQuery(projectId || "");
  const addMemberMutation = useAddMemberMutation(projectId || "");
  const updateMemberMutation = useUpdateMemberMutation(projectId || "");
  const removeMemberMutation = useRemoveMemberMutation(projectId || "");

  const [isInviteOpen, setIsInviteOpen] = useState(false);
  const [removingMember, setRemovingMember] = useState<Member | null>(null);

  // Set active project context on load
  React.useEffect(() => {
    if (projectDetail) {
      localStorage.setItem("activeProjectId", projectDetail.id);
      localStorage.setItem("activeProjectName", projectDetail.name);
    }
  }, [projectDetail]);

  const {
    register,
    handleSubmit,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<MemberFormValues>({
    resolver: zodResolver(memberSchema),
    defaultValues: { role: "viewer" },
  });


  if (isLoading) {
    return (
      <SidebarLayout>
        <div className="space-y-6">
          <Skeleton className="h-4 w-24 bg-muted/40" />
          <Card className="bg-card/50 border-border">
            <CardHeader>
              <Skeleton className="h-6 w-1/3 bg-muted/40" />
              <Skeleton className="h-4 w-1/2 bg-muted/40" />
            </CardHeader>
          </Card>
          <div className="space-y-2">
            <Skeleton className="h-10 w-full bg-muted/40" />
            <Skeleton className="h-12 w-full bg-muted/40" />
            <Skeleton className="h-12 w-full bg-muted/40" />
          </div>
        </div>
      </SidebarLayout>
    );
  }

  if (isError || !projectDetail) {
    return (
      <SidebarLayout>
        <div className="max-w-md mx-auto py-12 text-center space-y-4">
          <h2 className="text-lg font-bold text-destructive">Project Not Found</h2>
          <p className="text-sm text-muted-foreground">The project context may have been deleted or you do not have permission to view it.</p>
          <Button onClick={() => navigate("/projects")}>Back to Projects</Button>
        </div>
      </SidebarLayout>
    );
  }

  // Get current user's membership role
  const currentUserMember = projectDetail.members.find((m) => m.user_id === currentUser?.id);
  const currentUserRole: ProjectRole = currentUserMember?.role || "viewer";

  // Permission checks
  const isOwner = currentUserRole === "owner";
  const isAdmin = currentUserRole === "admin";
  const isReviewer = currentUserRole === "reviewer";
  const isViewer = currentUserRole === "viewer";
  const canManageMembers = isOwner || isAdmin;

  const onAddMemberSubmit = async (values: MemberFormValues) => {
    try {
      const res = await addMemberMutation.mutateAsync({
        email: values.email,
        role: values.role,
      });

      if (res.status === "invited") {
        toast.info("Invitation Sent", {
          description: "Collaborator is not registered. Pending project invitation recorded.",
        });
      } else {
        toast.success("Member added to project successfully.");
      }
      setIsInviteOpen(false);
      reset();
    } catch (err: any) {
      toast.error(err.message || "Failed to add member");
    }
  };

  const handleRoleChange = async (targetUser: Member, newRole: ProjectRole) => {
    try {
      await updateMemberMutation.mutateAsync({
        userId: targetUser.user_id,
        data: { role: newRole },
      });
      toast.success(`Role updated to ${newRole} for ${targetUser.username}`);
    } catch (err: any) {
      // Display backend errors directly (never suppress last owner errors)
      toast.error(err.message || "Failed to update role");
    }
  };

  const handleRemoveMember = async () => {
    if (!removingMember) return;
    try {
      await removeMemberMutation.mutateAsync(removingMember.user_id);
      toast.success(`${removingMember.username} removed from project`);
      setRemovingMember(null);
    } catch (err: any) {
      // Ensure backend owner protection errors are not suppressed
      toast.error(err.message || "Failed to remove member");
    }
  };

  // UI helpers
  const getRoleBadge = (role: ProjectRole) => {
    const styles: Record<ProjectRole, string> = {
      owner: "bg-red-500/10 text-red-500 border-red-500/20",
      admin: "bg-purple-500/10 text-purple-500 border-purple-500/20",
      reviewer: "bg-blue-500/10 text-blue-500 border-blue-500/20",
      viewer: "bg-gray-500/10 text-gray-500 border-gray-500/20",
    };
    return (
      <Badge variant="outline" className={styles[role]}>
        {role.toUpperCase()}
      </Badge>
    );
  };

  // Determine if active user can edit a member's role or remove them
  const canModifyMember = (targetMember: Member) => {
    if (isOwner) {
      return true; // Owner can edit anyone
    }
    if (isAdmin) {
      // Admin can only edit reviewers or viewers
      return targetMember.role === "reviewer" || targetMember.role === "viewer";
    }
    return false; // Reviewer and Viewer cannot modify anyone
  };

  return (
    <SidebarLayout>
      <div className="space-y-6">
        {/* Back Link */}
        <Link
          to="/projects"
          className="flex items-center gap-2 text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Projects</span>
        </Link>

        {/* Project Metadata Card */}
        <Card className="bg-card/50 backdrop-blur-xl border-border">
          <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="space-y-1">
              <CardTitle className="text-xl font-bold">{projectDetail.name}</CardTitle>
              <CardDescription className="text-xs">
                Created on {new Date(projectDetail.created_at).toLocaleDateString()}
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigate("/")}
              >
                <FileUp className="w-4 h-4 mr-2" />
                Upload Documents
              </Button>
              {canManageMembers && (
                <Button size="sm" onClick={() => setIsInviteOpen(true)}>
                  <UserPlus className="w-4 h-4 mr-2" />
                  Add Member
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {projectDetail.description || "No description provided for this project."}
            </p>
          </CardContent>
        </Card>

        {/* Members Table */}
        <Card className="bg-card/50 backdrop-blur-xl border-border overflow-hidden">
          <CardHeader>
            <CardTitle className="text-md font-semibold">Workspace Collaborators</CardTitle>
            <CardDescription className="text-xs">
              Manage member seats, access controls, and project administration.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-border bg-muted/20 text-[10px] font-semibold tracking-wider text-muted-foreground uppercase">
                    <th className="px-6 py-3">Member</th>
                    <th className="px-6 py-3">Email Address</th>
                    <th className="px-6 py-3">Role</th>
                    <th className="px-6 py-3">Joined Date</th>
                    <th className="px-6 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/65">
                  {projectDetail.members.map((member) => {
                    const editable = canModifyMember(member);
                    return (
                      <tr key={member.user_id} className="text-xs hover:bg-muted/10 transition-colors group">
                        <td className="px-6 py-4 flex items-center gap-3">
                          <Avatar className="w-8 h-8">
                            <AvatarFallback className="bg-primary/10 text-primary text-[10px] font-bold">
                              {member.username.substring(0, 2).toUpperCase()}
                            </AvatarFallback>
                          </Avatar>
                          <div>
                            <p className="font-semibold text-foreground flex items-center gap-1.5">
                              {member.username}
                              {member.user_id === currentUser?.id && (
                                <span className="text-[10px] text-muted-foreground font-normal bg-muted px-1.5 py-0.5 rounded">
                                  You
                                </span>
                              )}
                            </p>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-muted-foreground">{member.email}</td>
                        <td className="px-6 py-4">{getRoleBadge(member.role)}</td>
                        <td className="px-6 py-4 text-muted-foreground">
                          {new Date(member.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-6 py-4 text-right">
                          {editable && member.user_id !== currentUser?.id ? (
                            <div className="flex items-center justify-end gap-2">
                              {/* Change Role Selection */}
                              <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                  <Button variant="ghost" size="icon" className="w-8 h-8 rounded-full">
                                    <MoreVertical className="w-3.5 h-3.5" />
                                  </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent className="bg-card border-border">
                                  {isOwner && (
                                    <>
                                      <DropdownMenuItem onClick={() => handleRoleChange(member, "owner")}>
                                        Set Owner
                                      </DropdownMenuItem>
                                      <DropdownMenuItem onClick={() => handleRoleChange(member, "admin")}>
                                        Set Admin
                                      </DropdownMenuItem>
                                    </>
                                  )}
                                  <DropdownMenuItem onClick={() => handleRoleChange(member, "reviewer")}>
                                    Set Reviewer
                                  </DropdownMenuItem>
                                  <DropdownMenuItem onClick={() => handleRoleChange(member, "viewer")}>
                                    Set Viewer
                                  </DropdownMenuItem>
                                </DropdownMenuContent>
                              </DropdownMenu>

                              {/* Remove Collaborator */}
                              <Button
                                variant="ghost"
                                size="icon"
                                className="w-8 h-8 rounded-full text-red-500 hover:bg-red-50/10 hover:text-red-600"
                                onClick={() => setRemovingMember(member)}
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </Button>
                            </div>
                          ) : (
                            <span className="text-[10px] text-muted-foreground italic px-2">No actions</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        {/* Add / Invite Member Dialog */}
        <Dialog open={isInviteOpen} onOpenChange={setIsInviteOpen}>
          <DialogContent className="bg-card border-border sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle className="text-md font-semibold">Add Project Member</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit(onAddMemberSubmit)} className="space-y-4 pt-2">
              <div className="space-y-1">
                <Label htmlFor="email" className="text-xs">Collaborator Email *</Label>
                <Input
                  id="email"
                  placeholder="collaborator@example.com"
                  {...register("email")}
                  className="bg-card border-border"
                />
                {errors.email && <p className="text-[10px] text-destructive">{errors.email.message}</p>}
              </div>

              <div className="space-y-1">
                <Label htmlFor="role" className="text-xs">Access Role *</Label>
                <Select
                  defaultValue="viewer"
                  onValueChange={(val: any) => setValue("role", val)}
                >
                  <SelectTrigger className="bg-card border-border text-xs">
                    <SelectValue placeholder="Select access permissions" />
                  </SelectTrigger>
                  <SelectContent className="bg-card border-border">
                    {isOwner && (
                      <>
                        <SelectItem value="owner">Owner (Full Admin & Transfers)</SelectItem>
                        <SelectItem value="admin">Admin (Add / Edit Viewers & Reviewers)</SelectItem>
                      </>
                    )}
                    <SelectItem value="reviewer">Reviewer (Validate Facts & Resolve Conflicts)</SelectItem>
                    <SelectItem value="viewer">Viewer (Read-Only Access)</SelectItem>
                  </SelectContent>
                </Select>
                {errors.role && <p className="text-[10px] text-destructive">{errors.role.message}</p>}
              </div>

              <DialogFooter className="pt-2">
                <Button type="button" variant="outline" onClick={() => setIsInviteOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  Add Collaborator
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Remove Member Confirmation Alert */}
        <AlertDialog open={!!removingMember} onOpenChange={(open) => !open && setRemovingMember(null)}>
          <AlertDialogContent className="bg-card border-border">
            <AlertDialogHeader>
              <AlertDialogTitle className="text-md font-semibold">Remove Member from Project?</AlertDialogTitle>
              <AlertDialogDescription className="text-xs text-muted-foreground">
                This action will instantly revoke access for {removingMember?.username} to all claims, documents, and reports nested inside this project.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={handleRemoveMember} className="bg-red-600 hover:bg-red-700 text-white">
                Remove Access
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </SidebarLayout>
  );
};
export default ProjectDetail;
