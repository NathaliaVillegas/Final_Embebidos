#include <stdint.h>
#include <stdbool.h>

#include "inc/hw_memmap.h"
#include "inc/hw_ints.h"

#include "driverlib/sysctl.h"
#include "driverlib/gpio.h"
#include "driverlib/uart.h"
#include "driverlib/pin_map.h"
#include "driverlib/interrupt.h"

#include "driverlib/pwm.h"
#include "driverlib/sysctl.h"


volatile bool entregar_dulce = false;
volatile uint32_t total = 0;
volatile uint32_t respondidas = 0;
volatile uint32_t aciertos = 0;
volatile bool evento_r = false;
volatile bool evento_w = false;
volatile bool juego_activo = false;

#define PWM_DIVISOR 64
#define SERVO_FREQ 50

char buffer[20];
uint8_t idx = 0;


void Delay_ms(uint32_t ms){
    SysCtlDelay((120000000 / 3000) * ms);
}

void EnviarArduino(uint32_t valor)
{
    char numero[12];
    int i = 0;

    if (valor == 0) {
        numero[i++] = '0';
    } else {
        while (valor > 0) {
            numero[i++] = (valor % 10) + '0';
            valor /= 10;
        }
    }

    int inicio = 0;
    int fin = i - 1;
    while (inicio < fin) {
        char temp = numero[inicio];
        numero[inicio] = numero[fin];
        numero[fin] = temp;
        inicio++;
        fin--;
    }

    numero[i++] = '\n';
    numero[i] = '\0';

    int j = 0;
    while(numero[j] != '\0')
    {
        UARTCharPut(UART5_BASE, numero[j]);
        j++;
    }
}

void UART3IntHandler(void)
{
    uint32_t status = UARTIntStatus(UART3_BASE, true);
    UARTIntClear(UART3_BASE, status);

    while(UARTCharsAvail(UART3_BASE)){
        char c = UARTCharGetNonBlocking(UART3_BASE);
        
        if(c == '\n' || c == '\r'){
            buffer[idx] = '\0';
            idx = 0;
            
            if(buffer[0] == 'S'){
                uint32_t valor_temporal = 0;
                uint8_t i = 1;
                while(buffer[i] >= '0' && buffer[i] <= '9'){
                    valor_temporal = (valor_temporal * 10) + (buffer[i] - '0');
                    i++;
                }
                
                total = valor_temporal;
                aciertos = 0;
                respondidas = 0;
                juego_activo = true;
            }

            for(int i = 0; i < 20; i++){
                buffer[i] = '0';
            }
        }
        else{
            if(idx < sizeof(buffer)-1)
                buffer[idx++] = c;

            if(c == 'r') {
                idx = 0;
                if (juego_activo) {
                    evento_r = true;
                }
            }
            if(c == 'w') {
                idx = 0;
                if (juego_activo) {
                    evento_w = true;
                }
            }
        }
    }
}

void ConfigurarUARTArduino(void)
{
    SysCtlPeripheralEnable(SYSCTL_PERIPH_UART5);
    SysCtlPeripheralEnable(SYSCTL_PERIPH_GPIOC);

    while(!SysCtlPeripheralReady(SYSCTL_PERIPH_UART5));
    while(!SysCtlPeripheralReady(SYSCTL_PERIPH_GPIOC));

    GPIOPinConfigure(GPIO_PC6_U5RX);
    GPIOPinConfigure(GPIO_PC7_U5TX);

    GPIOPinTypeUART(GPIO_PORTC_BASE,
                    GPIO_PIN_6 | GPIO_PIN_7);

    UARTConfigSetExpClk(UART5_BASE, 120000000, 9600, UART_CONFIG_WLEN_8 | UART_CONFIG_STOP_ONE | UART_CONFIG_PAR_NONE);
}

void DarDulce(void)
{
    // 0°
    PWMPulseWidthSet(PWM0_BASE, PWM_OUT_1, 1875);
    Delay_ms(500);

    // 90°
    PWMPulseWidthSet(PWM0_BASE, PWM_OUT_1, 3750);
    Delay_ms(1200);

    // volver
    PWMPulseWidthSet(PWM0_BASE, PWM_OUT_1, 1875);
    Delay_ms(1200);
}



void EventoCorrecto(void){
    aciertos++;
    respondidas++;

    EnviarArduino(aciertos);

    GPIOPinWrite(GPIO_PORTK_BASE, 0x07, 0x01);
    Delay_ms(300);

    GPIOPinWrite(GPIO_PORTK_BASE, 0x07, 0x02);
    Delay_ms(300);

    GPIOPinWrite(GPIO_PORTK_BASE, 0x07, 0x04);
    Delay_ms(300);

    GPIOPinWrite(GPIO_PORTK_BASE, 0x07, 0x07);
    Delay_ms(300);

    GPIOPinWrite(GPIO_PORTK_BASE, 0x07, 0x00);
}



void EventoIncorrecto(void){
    respondidas++;

    GPIOPinWrite(GPIO_PORTM_BASE, 0x03, 0x03);
    Delay_ms(1000);
    GPIOPinWrite(GPIO_PORTM_BASE, 0x03, 0x00);
}


void ConfigurarHardware(void)
{
    IntMasterDisable();

    // PUERTO K
    SysCtlPeripheralEnable(SYSCTL_PERIPH_GPIOK);
    while(!SysCtlPeripheralReady(SYSCTL_PERIPH_GPIOK));

    GPIOPinTypeGPIOOutput(GPIO_PORTK_BASE,  0x07);
    GPIOPinWrite(GPIO_PORTK_BASE, 0x07, 0x00);

    // PUERTO M
    SysCtlPeripheralEnable(SYSCTL_PERIPH_GPIOM);
    while(!SysCtlPeripheralReady(SYSCTL_PERIPH_GPIOM));

    GPIOPinTypeGPIOOutput(GPIO_PORTM_BASE, 0x03);
    GPIOPinWrite(GPIO_PORTM_BASE, 0x03, 0x00);

    // UART3 Config
    SysCtlPeripheralEnable(SYSCTL_PERIPH_UART3);
    SysCtlPeripheralEnable(SYSCTL_PERIPH_GPIOA);
    
    while(!SysCtlPeripheralReady(SYSCTL_PERIPH_UART3));
    while(!SysCtlPeripheralReady(SYSCTL_PERIPH_GPIOA));

    GPIOPinConfigure(GPIO_PA4_U3RX);
    GPIOPinConfigure(GPIO_PA5_U3TX);
    GPIOPinTypeUART(GPIO_PORTA_BASE, 0x30);
    
    UARTConfigSetExpClk(UART3_BASE, 120000000, 9600, (UART_CONFIG_WLEN_8 | UART_CONFIG_STOP_ONE | UART_CONFIG_PAR_NONE));

    //interrupciones
    UARTIntClear(UART3_BASE, UART_INT_RX | UART_INT_RT);
    UARTIntEnable(UART3_BASE, UART_INT_RX | UART_INT_RT);
    IntEnable(INT_UART3);
}

void ConfigurarServo(void)
{
    SysCtlPeripheralEnable(SYSCTL_PERIPH_PWM0);
    SysCtlPeripheralEnable(SYSCTL_PERIPH_GPIOF);

    while(!SysCtlPeripheralReady(SYSCTL_PERIPH_PWM0));
    while(!SysCtlPeripheralReady(SYSCTL_PERIPH_GPIOF));

    // PF1 -> M0PWM1
    GPIOPinConfigure(GPIO_PF1_M0PWM1);
    GPIOPinTypePWM(GPIO_PORTF_BASE, GPIO_PIN_1);

    PWMClockSet(PWM0_BASE, PWM_SYSCLK_DIV_64);

    // 120MHz / 64 = 1.875MHz
    // 1.875MHz / 50Hz = 37500

    uint32_t periodo = 37500;

    PWMGenConfigure(PWM0_BASE, PWM_GEN_0, PWM_GEN_MODE_DOWN);

    PWMGenPeriodSet(PWM0_BASE, PWM_GEN_0, periodo);

    PWMPulseWidthSet(PWM0_BASE, PWM_OUT_1, 1875);
    PWMOutputState(PWM0_BASE, PWM_OUT_1_BIT, true);
    PWMGenEnable(PWM0_BASE, PWM_GEN_0);
}


int main(void)
{
    SysCtlClockFreqSet((SYSCTL_XTAL_25MHZ | SYSCTL_OSC_MAIN | SYSCTL_USE_PLL | SYSCTL_CFG_VCO_240), 120000000);

    ConfigurarHardware();
    ConfigurarUARTArduino();
    ConfigurarServo();
    IntMasterEnable();

    while(1){
        if(juego_activo){
            if(evento_r){
                evento_r = false;
                EventoCorrecto();
            }
            else if(evento_w){
                evento_w = false;
                EventoIncorrecto();
            }
        }

        if(juego_activo && respondidas >= total){
            juego_activo = false;

            if((aciertos * 100) >= (total * 60))
                entregar_dulce = true;
        }

        if(entregar_dulce) {
            entregar_dulce = false;
            DarDulce();
        }
        
        Delay_ms(20);
    }
}

