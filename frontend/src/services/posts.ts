import { api } from "@/services/api";
import type {
  CreatePostPayload,
  Post,
  PostStatus,
  ScheduledPost,
  SchedulePostPayload,
} from "@/types/post";

export async function createPost(payload: CreatePostPayload): Promise<Post> {
  const { data } = await api.post<Post>("/posts", payload);
  return data;
}

export async function listPosts(params?: {
  status?: PostStatus;
  offset?: number;
  limit?: number;
}): Promise<Post[]> {
  const { data } = await api.get<Post[]>("/posts", {
    params: {
      status_filter: params?.status,
      offset: params?.offset ?? 0,
      limit: params?.limit ?? 100,
    },
  });
  return data;
}

export async function getPost(postId: string): Promise<Post> {
  const { data } = await api.get<Post>(`/posts/${postId}`);
  return data;
}

export async function publishPost(postId: string): Promise<Post> {
  const { data } = await api.post<Post>(`/posts/${postId}/publish`);
  return data;
}

export async function schedulePost(
  postId: string,
  payload: SchedulePostPayload,
): Promise<ScheduledPost> {
  const { data } = await api.post<ScheduledPost>(`/posts/${postId}/schedule`, payload);
  return data;
}

export async function getScheduledPost(postId: string): Promise<ScheduledPost> {
  const { data } = await api.get<ScheduledPost>(`/posts/${postId}/schedule`);
  return data;
}

export async function cancelScheduledPost(postId: string): Promise<void> {
  await api.delete(`/posts/${postId}/schedule`);
}

export async function deletePost(postId: string): Promise<void> {
  await api.delete(`/posts/${postId}`);
}
