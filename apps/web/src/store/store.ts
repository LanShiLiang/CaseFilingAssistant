import { configureStore } from "@reduxjs/toolkit";

import { caseApi } from "./caseApi";

export function makeStore() {
  return configureStore({
    reducer: { [caseApi.reducerPath]: caseApi.reducer },
    middleware: (getDefaultMiddleware) => getDefaultMiddleware().concat(caseApi.middleware),
    // 敏感案件字段不进入持久化层，Redux 仅保存当前内存中的 API cache。
    devTools: process.env.NODE_ENV !== "production"
  });
}

export type AppStore = ReturnType<typeof makeStore>;
export type RootState = ReturnType<AppStore["getState"]>;
