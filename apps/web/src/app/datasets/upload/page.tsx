"use client";

import { Suspense } from "react";
import UploadDatasetPage from "./UploadClient";

export default function Page() {
  return (
    <Suspense fallback={<p className="text-atlas-muted">Loading uploader…</p>}>
      <UploadDatasetPage />
    </Suspense>
  );
}
