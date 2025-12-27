import availableJobsReducer from './jobs/availableJobSlice'
import initialPipelineConfigReducer from './jobs/currentPipeline'
import jobSchemaReducer from './jobs/jobSchemaSlice'
import { type Action, type ThunkAction, configureStore } from '@reduxjs/toolkit'

export const store = configureStore({
  reducer: {
    availableJobs: availableJobsReducer,
    jobSchemas: jobSchemaReducer,
    currentPipeline: initialPipelineConfigReducer
  },
})


// Infer the `RootState` and `AppDispatch` types from the store itself
export type RootState = ReturnType<typeof store.getState>
// Inferred type: {posts: PostsState, comments: CommentsState, users: UsersState}
export type AppDispatch = typeof store.dispatch
export type AppStore = typeof store;
export type AppThunk = ThunkAction<void, RootState, unknown, Action>