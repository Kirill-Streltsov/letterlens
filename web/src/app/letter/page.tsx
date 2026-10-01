"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";

import { LetterWorkspace } from "@/components/LetterWorkspace";
import { AppPage } from "@/components/Shell";
import {
  api,
  type CounsellingService,
  type Language,
  type LetterView,
  type Me,
  type Message,
  type QuestionResponse,
} from "@/lib/api";

