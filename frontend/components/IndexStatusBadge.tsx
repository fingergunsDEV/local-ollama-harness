"use client";

export interface IndexStatus {
  total_files_indexed: number;
  total_embeddings: number;
  embedded_files_count: number;
  max_files_limit: number;
}

export default function IndexStatusBadge({ status }: { status: IndexStatus | null }) {
  if (!status) return <span className="badge">index status unavailable</span>;
  return (
    <span className="badge">
      index {status.total_files_indexed}/{status.max_files_limit} files · {status.total_embeddings} vectors
    </span>
  );
}
