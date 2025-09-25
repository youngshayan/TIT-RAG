import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function Markdown({ content }: { content?: string }) {
  return (
    <div
      className="
        prose prose-slate max-w-none
        text-right [&_*]:text-right rtl
        [&_table]:w-full [&_table]:table-fixed
        [&_th]:text-center [&_td]:align-top
        [&_code]:break-words [&_pre]:overflow-auto
      "
      dir="rtl"
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {content || ""}
      </ReactMarkdown>
    </div>
  );
}
