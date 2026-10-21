/** Actions which several slices respond to. */
import { createAction } from "@reduxjs/toolkit";

/** The user gave a token for the api. */
export const tokenSupplied = createAction("auth/tokenSupplied");

/** The user took the token away. */
export const tokenForgotten = createAction("auth/tokenForgotten");
