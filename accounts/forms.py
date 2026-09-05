"""
Forms for admin-driven user management.
"""
from django import forms
from django.contrib.auth.models import Group, Permission

from .models import User, SystemRole


class AdminUserCreationForm(forms.ModelForm):
    """
    Form for admins to create new employee accounts.
    Admin sets username, password, role, profile photo, and group membership.
    """
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"placeholder": "Enter temporary password", "autocomplete": "new-password"}),
        min_length=6,
        help_text="Enter a temporary password. User will be forced to change it on first login by default.",
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={"placeholder": "Re-enter password", "autocomplete": "new-password"}),
        min_length=6,
        help_text="Re-enter the password to confirm.",
    )
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Assign user to groups for granular permissions.",
    )
    user_permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.select_related("content_type"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Assign specific direct permissions to this user.",
    )
    must_change_password = forms.BooleanField(
        required=False,
        initial=True,
        label="Require password change on first login",
        help_text="Forces the user to set a personal password upon first signing in.",
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "phone",
            "role",
            "profile_photo",
            "groups",
            "user_permissions",
            "is_active",
            "must_change_password",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = User.get_all_role_choices()

    def clean_username(self):
        username = self.cleaned_data.get("username", "").strip()
        if not username:
            raise forms.ValidationError("Username is required.")
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("A user with this username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with this email address already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password1")
        p2 = cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.must_change_password = self.cleaned_data.get("must_change_password", True)
        if commit:
            user.save()
            self.save_m2m()
        return user


class AdminUserChangeForm(forms.ModelForm):
    """
    Form for admins to edit existing user accounts.
    Allows editing profile, role, contact info, groups, direct permissions, and active status.
    Optionally allows resetting password directly in this form.
    """
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    user_permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.select_related("content_type"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    new_password = forms.CharField(
        label="Reset Password",
        required=False,
        widget=forms.PasswordInput(attrs={"placeholder": "Leave blank to keep current password", "autocomplete": "new-password"}),
        min_length=6,
        help_text="Leave blank unless you wish to reset this user's password.",
    )
    confirm_new_password = forms.CharField(
        label="Confirm Reset Password",
        required=False,
        widget=forms.PasswordInput(attrs={"placeholder": "Confirm new password", "autocomplete": "new-password"}),
        min_length=6,
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "phone",
            "role",
            "profile_photo",
            "groups",
            "user_permissions",
            "is_active",
            "must_change_password",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = User.get_all_role_choices()
        if self.instance and self.instance.pk:
            self.fields["groups"].initial = self.instance.groups.all()
            self.fields["user_permissions"].initial = self.instance.user_permissions.all()

    def clean_username(self):
        username = self.cleaned_data.get("username", "").strip()
        if not username:
            raise forms.ValidationError("Username is required.")
        exists = User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk).exists()
        if exists:
            raise forms.ValidationError("A user with this username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        if email:
            exists = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists()
            if exists:
                raise forms.ValidationError("A user with this email address already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        new_pwd = cleaned_data.get("new_password")
        conf_pwd = cleaned_data.get("confirm_new_password")
        if new_pwd:
            if not conf_pwd:
                self.add_error("confirm_new_password", "Please confirm the new password.")
            elif new_pwd != conf_pwd:
                self.add_error("confirm_new_password", "Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        new_pwd = self.cleaned_data.get("new_password")
        if new_pwd:
            user.set_password(new_pwd)
            # If admin reset password, default must_change_password to True unless explicitly unchecked
            if "must_change_password" not in self.cleaned_data:
                user.must_change_password = True
        if commit:
            user.save()
            self.save_m2m()
        return user


class PasswordChangeOnFirstLoginForm(forms.Form):
    """
    Form for users to change their password on first login.
    """
    new_password = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={"placeholder": "Enter at least 8 characters", "autocomplete": "new-password"}),
        min_length=8,
        help_text="Minimum 8 characters. Include numbers and letters for safety.",
    )
    confirm_password = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={"placeholder": "Re-enter new password", "autocomplete": "new-password"}),
        min_length=8,
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")
        if new_password and confirm_password:
            if new_password != confirm_password:
                raise forms.ValidationError("Passwords do not match. Please verify and re-enter.")
            if len(new_password) < 8:
                raise forms.ValidationError("Password must be at least 8 characters long.")
        return cleaned_data


class SystemRoleCreationForm(forms.ModelForm):
    """
    Form for administrators to create a new System Role,
    with an optional linked permission group and initial permissions.
    """
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.select_related("content_type"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Default permissions bundled with this role.",
    )
    create_group = forms.BooleanField(
        required=False,
        initial=True,
        label="Create matching permission group",
        help_text="Automatically creates a functional group bundling the selected permissions.",
    )

    class Meta:
        model = SystemRole
        fields = [
            "name",
            "code",
            "description",
            "is_admin",
        ]

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise forms.ValidationError("Role name is required.")
        if SystemRole.objects.filter(name__iexact=name).exists():
            raise forms.ValidationError("A role with this name already exists.")
        return name

    def clean_code(self):
        code = self.cleaned_data.get("code", "").strip()
        name = self.cleaned_data.get("name", "").strip()
        if not code and name:
            code = name.upper().replace(" ", "_").replace("-", "_")
        if code and SystemRole.objects.filter(code__iexact=code).exists():
            raise forms.ValidationError("A role with this code already exists.")
        return code

    def save(self, commit=True):
        role = super().save(commit=False)
        if not role.code:
            role.code = role.name.strip().upper().replace(" ", "_").replace("-", "_")

        if commit:
            create_group = self.cleaned_data.get("create_group", True)
            group = None
            if create_group:
                group, _ = Group.objects.get_or_create(name=role.name)
                perms = self.cleaned_data.get("permissions")
                if perms:
                    group.permissions.set(perms)
            role.group = group
            role.save()
        return role
