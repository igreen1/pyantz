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
import type { Job } from "./pipelineTypes";
import { standardDataTypes } from "json-edit-react";

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
        addNode: (state, action: PayloadAction<Node>) => {
            state.nodes = [
                action.payload,
                ...state.nodes
            ];
        },
        addEdge: (state, action: PayloadAction<Edge>) => {
            state.edges = [
                action.payload,
                ...state.edges
            ]
        },
        updateJobNode: (state, action: PayloadAction<{id: string; job: Job}>) => {
            const {id, job } = action.payload;
            const node = state.nodes.find((n) => n.id === id);
            if (node) {
                console.log("updating node");
                node.data = {
                    ...node.data,
                    job: {
                        ...(node.data?.job ?? {}),
                        job
                    }
                }
            }
        },
        deleteJobNode: (state, action: PayloadAction<string>) => {
            console.log("trying to delete!");
            const node_id = action.payload;
            console.log(node_id);
            state.nodes = state.nodes.filter((n) => n.id !== node_id);
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
    addEdge,
    addNode,
    deleteJobNode,
    setEdges,
    setNodes,
    updateEdges,
    updateNodes,
    updateJobNode,
} = graphSlice.actions

export default graphSlice.reducer;
