-- Create users table FIRST (no dependencies)
CREATE TABLE `users` (
`id` CHAR(36) NOT NULL,
`email` VARCHAR(255) NOT NULL,
`password_hash` VARCHAR(255) NOT NULL,
`created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
`updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
PRIMARY KEY (`id`),
UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Create habits table SECOND (depends on users)
CREATE TABLE `habits` (
`id` CHAR(36) NOT NULL,
`user_id` CHAR(36) NOT NULL,
`name` VARCHAR(255) NOT NULL,
`created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
PRIMARY KEY (`id`),
KEY `user_id` (`user_id`),
CONSTRAINT `fk_habits_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Create habit_completions table LAST (depends on habits)
CREATE TABLE `habit_completions` (
`id` CHAR(36) NOT NULL,
`habit_id` CHAR(36) NOT NULL,
`completion_date` DATE NOT NULL,
`is_completed` TINYINT(1) NOT NULL DEFAULT 0,
`created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
`updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
PRIMARY KEY (`id`),
KEY `habit_id` (`habit_id`),
CONSTRAINT `fk_completions_habit` FOREIGN KEY (`habit_id`) REFERENCES `habits`(`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;