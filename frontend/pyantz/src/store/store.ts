import availableJobsReducer from './slices/availableJobSlice'
import initialPipelineConfigReducer from './slices/currentPipeline'
import jobSchemaReducer from './slices/jobSchemaSlice'
import UiOptionsReducer from './slices/uiSlice'
import { type Action, type ThunkAction, configureStore } from '@reduxjs/toolkit'

export const store = configureStore({
  reducer: {
    availableJobs: availableJobsReducer,
    jobSchemas: jobSchemaReducer,
    currentPipeline: initialPipelineConfigReducer,
    uiOptions: UiOptionsReducer,
  },
})


// Infer the `RootState` and `AppDispatch` types from the store itself
export type RootState = ReturnType<typeof store.getState>
// Inferred type: {posts: PostsState, comments: CommentsState, users: UsersState}
export type AppDispatch = typeof store.dispatch
export type AppStore = typeof store;
export type AppThunk = ThunkAction<void, RootState, unknown, Action>