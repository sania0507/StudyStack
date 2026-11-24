/*
  ============================================================
  src/api/types.ts  —  the shapes that cross the network
  ============================================================
  These types are what components render. `client.ts` converts
  the backend's snake_case responses into these camelCase
  shapes, so pages never deal with `domain_id` or `due_date`.

  Keeping them separate from mock.ts means switching a page
  from fake data to the real API never changes the types.
*/

export type User = {
  id: string
  name: string
  email: string
  avatarUrl: string
  joinedAt: string
}

export type Domain = {
  id: string
  name: string
  colour: string // a token name, e.g. "violet"
  minutesThisWeek: number
  /** A daily routine: its tasks untick themselves each new day. */
  repeatsDaily: boolean
}

export type Subtask = {
  id: string
  title: string
  completed: boolean
  taskId: string
}

export type Task = {
  id: string
  domainId: string
  title: string
  completed: boolean
  dueDate?: string // "YYYY-MM-DD" — optional deadline
  remindAt?: string // "YYYY-MM-DDTHH:mm" — optional reminder
  overdue?: boolean // derived by the backend, never stored
  subtasks: Subtask[]
}

export type Session = {
  id: string
  domainId: string
  minutes: number
  finishedAt: string // ISO string
}

export type VisionItem = {
  id: string
  caption: string | null
  /** Percentage of the board width, 0..100. */
  x: number
  /** Percentage of the board height, 0..100. */
  y: number
  /** Percentage of the board width, 6..60. Height follows the image ratio. */
  width: number
}

export type NoteFolder = {
  id: string
  name: string
  noteCount: number
}

export type Note = {
  id: string
  folderId: string
  title: string
  body: string
  pinned: boolean
  /** Manual drag order. Never affects createdAt. */
  position: number
  createdAt: string
  updatedAt: string
}
