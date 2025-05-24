import * as z from "zod";

const passwordSchema = z
  .string({
    required_error: "Password is required",
    invalid_type_error: "Password must be a string",
  })
  .min(8, { message: "Password must be at least 8 characters long" })
  .refine((password) => /[A-Z]/.test(password), {
    message: "Password must contain at least one uppercase letter",
  })
  .refine((password) => /[a-z]/.test(password), {
    message: "Password must contain at least one lowercase letter",
  })
  .refine((password) => /[0-9]/.test(password), {
    message: "Password must contain at least one number",
  })
  .refine(
    (password) => /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password),
    { message: "Password must contain at least one special character" }
  );

// Define a schema for sign-up validation
export const signUpSchema = z
  .object({
    email: z.string().email({ message: "Enter a valid email" }),
    password: passwordSchema,
    password_confirmation: z.string(),
    terms: z.boolean().default(false).optional(),
  })
  .refine((data) => data.password === data.password_confirmation, {
    message: "Passwords do not match",
    path: ["password_confirmation"],
  });

// Define a schema for sign-in validation
export const signInSchema = z.object({
  email: z.string().email({ message: "Enter a valid email" }),
  password: passwordSchema,
  rememberMe: z.boolean().default(false).optional(),
});

export const forgotPasswordSchema = z.object({
  email: z.string().email({ message: "Enter a valid email" }),
});

export const resetPasswordSchema = z.object({
  new_password: passwordSchema,
  confirm_password: z.string(),
}).refine((data) => data.new_password === data.confirm_password, {
  message: "Passwords do not match",
  path: ["confirm_password"],
});

export const updatePasswordSchema = z.object({
  current_password: z.string().min(1, { message: "Current password is required" }),
  new_password: passwordSchema,
  confirm_password: z.string(),
}).refine((data) => data.new_password === data.confirm_password, {
  message: "Passwords do not match",
  path: ["confirm_password"],
});

export const verificationCodeSchema = z.object({
  code: z.string().min(4, {
    message: "Invalid verification code.",
  }),
  userEmail: z.string().optional(),
});

export const profileUpdateSchema = z.object({
  first_name: z.string().trim().min(1, { message: "Firstname is required" }),
  last_name: z.string().trim().min(1, { message: "Lastname is required" }),
  preferences: z.string().optional(),
  phone_number: z
    .string()
    .trim()
    .regex(/^\+?\d[\d\s\-()]{7,}$/, {
      message: "Phone number must be in a valid international format",
    }),
});
