"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { queryKeys } from "@/lib/query-keys"

import { deletePaper, listPapers, retryPaper, uploadPaper } from "./api"
import { IN_PROGRESS_STATUSES, type Paper } from "./types"

const POLL_INTERVAL_MS = 2500

export function usePapers() {
  return useQuery({
    queryKey: queryKeys.papers,
    queryFn: listPapers,
    // Poll only while something is moving through ingestion or deletion.
    refetchInterval: (query) =>
      query.state.data?.some((paper) => IN_PROGRESS_STATUSES.includes(paper.status))
        ? POLL_INTERVAL_MS
        : false,
  })
}

export function useIndexedPapers(): { papers: Paper[]; isLoading: boolean } {
  const { data, isLoading } = usePapers()
  return {
    papers: (data ?? []).filter((paper) => paper.status === "indexed"),
    isLoading,
  }
}

export function useUploadPaper() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: uploadPaper,
    onSettled: () => queryClient.invalidateQueries({ queryKey: queryKeys.papers }),
  })
}

export function useDeletePaper() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deletePaper,
    onSettled: () => queryClient.invalidateQueries({ queryKey: queryKeys.papers }),
  })
}

export function useRetryPaper() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: retryPaper,
    onSettled: () => queryClient.invalidateQueries({ queryKey: queryKeys.papers }),
  })
}
