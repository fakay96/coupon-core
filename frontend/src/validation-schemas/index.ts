// Import the zod library for schema validation
import * as z from "zod";

// Define a schema for user settings validation
export const SettingsSchema = z
  .object({
    name: z.optional(z.string()),
    isTwoFactorEnabled: z.optional(z.boolean()),
    role: z.enum(["ADMIN", "USER"]),
    email: z.optional(z.string().email()),
    password: z.optional(z.string().min(6)),
    newPassword: z.optional(z.string().min(6)),
  })
  .refine(
    (data) => {
      if (data.password && !data.newPassword) return false;

      return true;
    },
    {
      message: "New password is required!",
      path: ["newPassword"],
    }
  )
  .refine(
    (data) => {
      if (data.newPassword && !data.password) return false;

      return true;
    },
    {
      message: "Password is required!",
      path: ["password"],
    }
  );

// Define a schema for new password validation
export const NewPasswordSchema = z.object({
  password: z.string().min(6, { message: "Minimum of 6 characters required" }),
});

// Define a schema for password reset validation
export const ResetSchema = z.object({
  email: z.string().email({ message: "Email is required." }),
});

// Define a schema for login validation
export const LoginSchema = z.object({
  email: z.string().email({ message: "Email is required." }),
  password: z.string().min(1, { message: "Password is required" }),
  code: z.optional(z.string()),
});

// Define a schema for user registration validation
export const RegisterSchema = z.object({
  name: z.string().min(1, {
    message: "Name is required",
  }),
  email: z.string().email({ message: "Email is required." }),
  password: z.string().min(6, { message: "Minimum 6 characters required" }),
});

// Define a schema for sign-up validation
export const signUpSchema = z.object({
  firstname: z.string().min(2, { message: "Enter a valid firstname" }).max(50),
  lastname: z.string().min(2, { message: "Enter a valid lastname" }).max(50),
  email: z.string().email({ message: "Enter a valid email" }),
  password: z
    .string()
    .min(8, { message: "Enter minimum of 8 characters" })
    .max(50),
  terms: z.boolean().default(false).optional(),
});

// Define a schema for review validation
export const reviewSchema = z.object({
  name: z.string({ message: "Enter a valid email" }),
  email: z.string().email({ message: "Enter a valid email" }),
  review: z.string({ message: "Enter a valid values" }),
});

// Define a schema for sign-in validation
export const signInSchema = z.object({
  email: z.string().email({ message: "Enter a valid email" }),
  password: z
    .string()
    .min(8, { message: "Enter minimum of 8 characters" })
    .max(50),
  rememberMe: z.boolean().default(false).optional(),
});


export const forgotPasswordSchema = z.object({
  email: z.string().email({ message: "Enter a valid email" }),
});


export const verificationCodeSchema = z.object({
  pin: z.string().min(4, {
    message: "Your one-time password must be 4 characters.",
  }),
})