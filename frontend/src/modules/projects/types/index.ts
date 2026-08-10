export type ProjectRole = "owner" | "admin" | "reviewer" | "viewer";

export interface Project {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface Member {
  user_id: string;
  username: string;
  email: string;
  role: ProjectRole;
  created_at: string;
}

export interface ProjectDetail extends Project {
  members: Member[];
}

export interface ProjectCreateInput {
  name: string;
  description?: string;
}

export interface ProjectUpdateInput {
  name?: string;
  description?: string;
}

export interface MemberAddInput {
  email: string;
  role: ProjectRole;
}

export interface MemberUpdateInput {
  role: ProjectRole;
}
