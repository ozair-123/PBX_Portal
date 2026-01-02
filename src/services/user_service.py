"""User service for managing user and extension lifecycle."""

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import EmailStr

from ..models.user import User
from ..models.extension import Extension
from ..config import Config
from .extension_allocator import allocate_extension

logger = logging.getLogger(__name__)


class UserService:
    """Service for managing users and their extensions."""

    @staticmethod
    def create_user(session: Session, name: str, email: str) -> Dict[str, Any]:
        """
        Create a new user with an automatically allocated extension.

        This method:
        1. Validates input (name, email)
        2. Starts a database transaction
        3. Creates the User record
        4. Calls ExtensionAllocator to allocate an extension
        5. Commits the transaction
        6. Returns the user with extension details

        Args:
            session: SQLAlchemy database session
            name: User's full name
            email: User's email address (must be unique)

        Returns:
            Dict containing user and extension details:
            {
                "id": UUID,
                "tenant_id": UUID,
                "name": str,
                "email": str,
                "created_at": datetime,
                "extension": {
                    "id": UUID,
                    "number": int,
                    "secret": str,
                    "created_at": datetime
                }
            }

        Raises:
            ValueError: If email is already in use or validation fails
            RuntimeError: If extension allocation fails after retries
        """
        # Input validation
        if not name or not name.strip():
            raise ValueError("Name cannot be empty")

        if not email or not email.strip():
            raise ValueError("Email cannot be empty")

        email = email.strip().lower()

        logger.info(f"Creating user with name='{name}', email='{email}'")

        try:
            # Create user record
            user = User(
                tenant_id=Config.DEFAULT_TENANT_ID,
                name=name.strip(),
                email=email
            )
            session.add(user)
            session.flush()  # Flush to get user.id for extension allocation

            logger.info(f"User created with id={user.id}")

            # Allocate extension for this user
            extension = allocate_extension(session, str(user.id))

            # Commit transaction
            session.commit()

            logger.info(
                f"User {user.id} created successfully with extension {extension.number}"
            )

            # Return user with extension details
            return {
                "id": str(user.id),
                "tenant_id": str(user.tenant_id),
                "name": user.name,
                "email": user.email,
                "created_at": user.created_at.isoformat(),
                "extension": {
                    "id": str(extension.id),
                    "number": extension.number,
                    "secret": extension.secret,
                    "created_at": extension.created_at.isoformat()
                }
            }

        except IntegrityError as e:
            session.rollback()
            # Check if email uniqueness constraint was violated
            if "email" in str(e.orig).lower() or "unique" in str(e.orig).lower():
                logger.warning(f"Email already exists: {email}")
                raise ValueError(f"Email '{email}' is already in use")
            else:
                logger.error(f"Database integrity error creating user: {str(e)}")
                raise ValueError(f"Failed to create user due to data conflict: {str(e)}")

        except Exception as e:
            session.rollback()
            logger.error(f"Error creating user: {str(e)}")
            raise

    @staticmethod
    def list_all_users(session: Session) -> List[Dict[str, Any]]:
        """
        Retrieve all users with their assigned extensions.

        Args:
            session: SQLAlchemy database session

        Returns:
            List of user dictionaries with extension details

        Raises:
            RuntimeError: If database query fails
        """
        try:
            # Query all users with their extensions (joined)
            users = session.query(User).all()

            result = []
            for user in users:
                user_dict = {
                    "id": str(user.id),
                    "tenant_id": str(user.tenant_id),
                    "name": user.name,
                    "email": user.email,
                    "created_at": user.created_at.isoformat(),
                    "extension": None
                }

                # Add extension if it exists (should always exist in normal flow)
                if user.extension:
                    user_dict["extension"] = {
                        "id": str(user.extension.id),
                        "number": user.extension.number,
                        "secret": user.extension.secret,
                        "created_at": user.extension.created_at.isoformat()
                    }

                result.append(user_dict)

            logger.info(f"Retrieved {len(result)} users")
            return result

        except Exception as e:
            logger.error(f"Error listing users: {str(e)}")
            raise RuntimeError(f"Failed to retrieve users: {str(e)}")

    @staticmethod
    def delete_user(session: Session, user_id: str) -> Dict[str, Any]:
        """
        Delete a user and free their extension for reuse.

        The extension is automatically deleted via CASCADE relationship.

        Args:
            session: SQLAlchemy database session
            user_id: UUID of the user to delete

        Returns:
            Dict containing deletion details:
            {
                "message": str,
                "deleted_user_id": str,
                "freed_extension": int
            }

        Raises:
            ValueError: If user not found
            RuntimeError: If deletion fails
        """
        try:
            # Find user by ID
            user = session.query(User).filter(User.id == user_id).first()

            if not user:
                logger.warning(f"User not found: {user_id}")
                raise ValueError(f"User with id '{user_id}' not found")

            # Get extension number before deletion (for response)
            freed_extension = user.extension.number if user.extension else None

            logger.info(
                f"Deleting user {user_id} (email={user.email}, extension={freed_extension})"
            )

            # Delete user (cascade deletes extension)
            session.delete(user)
            session.commit()

            logger.info(
                f"User {user_id} deleted successfully, extension {freed_extension} freed"
            )

            return {
                "message": "User deleted successfully",
                "deleted_user_id": user_id,
                "freed_extension": freed_extension
            }

        except ValueError:
            # Re-raise ValueError (user not found)
            raise

        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting user {user_id}: {str(e)}")
            raise RuntimeError(f"Failed to delete user: {str(e)}")
