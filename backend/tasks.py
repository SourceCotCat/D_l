from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings


@shared_task
def send_registration_email(user_email, first_name):
    # отправляем приветственное письмо после регистрации
    send_mail(
        subject='Регистрация на сервисе закупок',
        message=f'Здравствуйте, {first_name}! Вы успешно зарегистрировались.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user_email],
        fail_silently=True,
    )


@shared_task
def send_order_confirmation_email(user_email, order_id, items_text, total, contact_str):
    # письмо покупателю с подтверждением заказа
    send_mail(
        subject=f'Подтверждение заказа #{order_id}',
        message=(
            f'Ваш заказ #{order_id} подтверждён.\n\n'
            f'Товары:\n{items_text}\n\n'
            f'Итого: {total} руб.\n\n'
            f'Адрес доставки: {contact_str}'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user_email],
        fail_silently=True,
    )


@shared_task
def send_order_invoice_email(order_id, user_email, items_text, total, contact_str):
    # накладная администратору для исполнения заказа
    send_mail(
        subject=f'Новый заказ #{order_id}',
        message=(
            f'Получен новый заказ #{order_id} от {user_email}.\n\n'
            f'Товары:\n{items_text}\n\n'
            f'Итого: {total} руб.\n\n'
            f'Адрес доставки: {contact_str}'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.ADMIN_EMAIL],
        fail_silently=True,
    )


@shared_task
def send_order_status_email(user_email, order_id, status_display):
    # уведомление покупателю об изменении статуса заказа
    send_mail(
        subject=f'Статус заказа #{order_id} изменён',
        message=f'Статус вашего заказа #{order_id} изменён на «{status_display}».',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user_email],
        fail_silently=True,
    )
