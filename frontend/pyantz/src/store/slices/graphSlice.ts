/**
 * Stores state that affects what shows on screen.
 */

import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import {
    applyNodeChanges, 
    applyEdgeChanges, 
    type Node,
    type Edge,
} from "@xyflow/react";

export interface JobGraph {
    nodes: Node[];
    edges: Edge[];
}

const initialState: JobGraph = {
    nodes: [],
    edges: [],
}

export const graphSlice = createSlice({
    name: "uiOptions",
    initialState,
    reducers: {
        setNodes: (state, action: PayloadAction<Node[]>) => {
            state.nodes = action.payload;
        },
        setEdges: (state, action: PayloadAction<Edge[]>) => {
            state.edges = action.payload;
        },
        
        updateNodes: (state, action) => {
            state.nodes = applyNodeChanges(action.payload, state.nodes); // Apply changes to the store's state
        },
        updateEdges: (state, action) => {
            state.edges = applyEdgeChanges(action.payload, state.edges);
        },
    }
})

export const {
    setEdges,
    setNodes,
    updateEdges,
    updateNodes,
} = graphSlice.actions

export default graphSlice.reducer;
