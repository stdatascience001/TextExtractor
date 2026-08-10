import axiosInstance from "@/shared/lib/axios";
import {
  Project,
  ProjectDetail,
  ProjectCreateInput,
  ProjectUpdateInput,
  Member,
  MemberAddInput,
  MemberUpdateInput,
} from "../types";

export const projectApi = {
  async getProjects(): Promise<Project[]> {
    const res = await axiosInstance.get("/projects");
    return res.data;
  },

  async getProject(projectId: string): Promise<ProjectDetail> {
    const res = await axiosInstance.get(`/projects/${projectId}`);
    return res.data;
  },

  async createProject(data: ProjectCreateInput): Promise<Project> {
    const res = await axiosInstance.post("/projects", data);
    return res.data;
  },

  async updateProject(projectId: string, data: ProjectUpdateInput): Promise<Project> {
    const res = await axiosInstance.put(`/projects/${projectId}`, data);
    return res.data;
  },

  async deleteProject(projectId: string): Promise<void> {
    await axiosInstance.delete(`/projects/${projectId}`);
  },

  async getMembers(projectId: string, skip: number = 0, limit: number = 10): Promise<Member[]> {
    const res = await axiosInstance.get(`/projects/${projectId}/members?skip=${skip}&limit=${limit}`);
    return res.data;
  },

  async addMember(projectId: string, data: MemberAddInput): Promise<{ status: string; message: string }> {
    const res = await axiosInstance.post(`/projects/${projectId}/members`, data);
    return res.data;
  },

  async updateMember(projectId: string, userId: string, data: MemberUpdateInput): Promise<void> {
    await axiosInstance.patch(`/projects/${projectId}/members/${userId}`, data);
  },

  async removeMember(projectId: string, userId: string): Promise<void> {
    await axiosInstance.delete(`/projects/${projectId}/members/${userId}`);
  },
};
