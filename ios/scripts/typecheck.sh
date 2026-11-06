#!/usr/bin/env bash
# Typecheck the iOS app against the iOS simulator SDK without a simulator runtime.
# Use it where `xcodebuild` cannot find a destination (CI without iOS runtimes).
set -euo pipefail
cd "$(dirname "$0")/.."
SDK=$(xcrun --sdk iphonesimulator --show-sdk-path)
ARCH=$(uname -m)
TARGET="${ARCH}-apple-ios17.0-simulator"
OUT=build/typecheck
mkdir -p "$OUT"
xcrun --sdk iphonesimulator swiftc -emit-module -parse-as-library -swift-version 6 \
  -module-name LetterLensCore -target "$TARGET" -sdk "$SDK" \
  -emit-module-path "$OUT/LetterLensCore.swiftmodule" \
  Packages/LetterLensCore/Sources/LetterLensCore/*.swift
xcrun --sdk iphonesimulator swiftc -typecheck -parse-as-library -swift-version 5 \
  -module-name LetterLens -target "$TARGET" -sdk "$SDK" -I "$OUT" \
  LetterLens/App/*.swift LetterLens/Services/*.swift LetterLens/Views/*.swift
echo "iOS app typechecks against $(basename "$SDK")"
