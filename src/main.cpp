#include <Arduino.h>

/*
  adc_device

  Running on a Seeeduino Xiao
  
  Listens for input on trigger, and acquires data at those time points. Can handle up to 31khz before it has a really
  hard time. 

  Listens for instruction on number of points to gather, and when to return the data. Instructions are in the format
  of a letter followed by several integers. 

  - GX: returns the data in the buffer, 0:X, as a 16-bit integer. 
  - RX: places the value X into num_points variable, then readies data acquisition

  The circuit:
  * external trigger connected to pin 8
  * analog input to pin 0 (A0/PA02)

  Created 6-18-21
  By Magnus Wood
  Modified 11-17-21
  

  Part of the pi-spec device:
  https://github.com/fieryWalrus1002/pi-spec/

*/

//////////////////////////// ADC variables ///////////////////////////////////////////////////
const int adc_trig_pin = 8; // the trigger pulse will come into this pin from the other arduino

volatile int cnt = 0; // counter

int measure_state = 0; // is the device in acquisition mode or listen mode?

volatile int data_ready = 0; // the flag for the adc having a value ready to read
volatile uint16_t data[10000];

long prev_time;
long trace_start;
long pulse_interval_time = 250; // holds teh pulse interval time, for calculating the time axis of the data when sending
int num_points = 1000;          // max points we are measuring
long time_elapsed;
int data_ready_for_export = 0; // flag for data transfer to program

int current_num = 0; // when transferring data to the python gui, this is where the data will start transferring

/////////////////////// input state machine variables ////////////////////////////////////////
// the states of our input state-machine
// G is get data, R is ready capture
typedef enum
{
    NONE,
    GOT_G,
    GOT_R,

} states;
states state = NONE;
int current_value = 0;

////////////////////////////////////////////// functions //////////////////////////////////////////////////////////

void clock_init()
{
    /* Set the correct number of wait states for 48 MHz @ 3.3v */
    NVMCTRL->CTRLB.bit.RWS = 1;

    /* This works around a quirk in the hardware (errata 1.2.1) -
     the DFLLCTRL register must be manually reset to this value before
     configuration. */
    while (!SYSCTRL->PCLKSR.bit.DFLLRDY)
        ;
    SYSCTRL->DFLLCTRL.reg = SYSCTRL_DFLLCTRL_ENABLE;
    while (!SYSCTRL->PCLKSR.bit.DFLLRDY)
        ;

    /* Write the coarse and fine calibration from NVM. */
    uint32_t coarse =
        ((*(uint32_t *)FUSES_DFLL48M_COARSE_CAL_ADDR) & FUSES_DFLL48M_COARSE_CAL_Msk) >> FUSES_DFLL48M_COARSE_CAL_Pos;
    uint32_t fine =
        ((*(uint32_t *)FUSES_DFLL48M_FINE_CAL_ADDR) & FUSES_DFLL48M_FINE_CAL_Msk) >> FUSES_DFLL48M_FINE_CAL_Pos;

    SYSCTRL->DFLLVAL.reg = SYSCTRL_DFLLVAL_COARSE(coarse) | SYSCTRL_DFLLVAL_FINE(fine);

    /* Wait for the write to finish. */
    while (!SYSCTRL->PCLKSR.bit.DFLLRDY)
    {
    };

    SYSCTRL->DFLLCTRL.reg |=
        /* Enable USB clock recovery mode */
        SYSCTRL_DFLLCTRL_USBCRM |
        /* Disable chill cycle as per datasheet to speed up locking.
       This is specified in section 17.6.7.2.2, and chill cycles
       are described in section 17.6.7.2.1. */
        SYSCTRL_DFLLCTRL_CCDIS;

    /* Configure the DFLL to multiply the 1 kHz clock to 48 MHz */
    SYSCTRL->DFLLMUL.reg =
        /* This value is output frequency / reference clock frequency,
         so 48 MHz / 1 kHz */
        SYSCTRL_DFLLMUL_MUL(48000) |
        /* The coarse and fine values can be set to their minimum
         since coarse is fixed in USB clock recovery mode and
         fine should lock on quickly. */
        SYSCTRL_DFLLMUL_FSTEP(1) |
        SYSCTRL_DFLLMUL_CSTEP(1);

    /* Closed loop mode */
    SYSCTRL->DFLLCTRL.bit.MODE = 1;

    /* Enable the DFLL */
    SYSCTRL->DFLLCTRL.bit.ENABLE = 1;

    /* Wait for the write to complete */
    while (!SYSCTRL->PCLKSR.bit.DFLLRDY)
    {
    };

    /* Setup GCLK0 using the DFLL @ 48 MHz */
    GCLK->GENCTRL.reg =
        GCLK_GENCTRL_ID(0) |
        GCLK_GENCTRL_SRC_DFLL48M |
        /* Improve the duty cycle. */
        GCLK_GENCTRL_IDC |
        GCLK_GENCTRL_GENEN;

    /* Wait for the write to complete */
    while (GCLK->STATUS.bit.SYNCBUSY)
    {
    };

    /* Configure GCLK2's divider - in this case, no division - so just divide by one */
    GCLK->GENDIV.reg =
        GCLK_GENDIV_ID(2) |
        GCLK_GENDIV_DIV(1);

    /* Setup GCLK2 using the internal 8 MHz oscillator */
    GCLK->GENCTRL.reg =
        GCLK_GENCTRL_ID(2) |
        GCLK_GENCTRL_SRC_OSC8M |
        /* Improve the duty cycle. */
        GCLK_GENCTRL_IDC |
        GCLK_GENCTRL_GENEN;

    /* Wait for the write to complete */
    while (GCLK->STATUS.bit.SYNCBUSY)
    {
    };

    /* Connect GCLK2 to ADC */
    GCLK->CLKCTRL.reg =
        GCLK_CLKCTRL_CLKEN |
        GCLK_CLKCTRL_GEN_GCLK2 |
        GCLK_CLKCTRL_ID_ADC;

    /* Wait for the write to complete. */
    while (GCLK->STATUS.bit.SYNCBUSY)
    {
    };
}

void ADC_init()
{
    /* Enable the APB clock for the ADC. */
    PM->APBCMASK.reg |= PM_APBCMASK_ADC;

    uint32_t bias = (*((uint32_t *)ADC_FUSES_BIASCAL_ADDR) & ADC_FUSES_BIASCAL_Msk) >> ADC_FUSES_BIASCAL_Pos;
    uint32_t linearity = (*((uint32_t *)ADC_FUSES_LINEARITY_0_ADDR) & ADC_FUSES_LINEARITY_0_Msk) >> ADC_FUSES_LINEARITY_0_Pos;
    linearity |= ((*((uint32_t *)ADC_FUSES_LINEARITY_1_ADDR) & ADC_FUSES_LINEARITY_1_Msk) >> ADC_FUSES_LINEARITY_1_Pos) << 5;

    /* Wait for bus synchronization. */
    while (ADC->STATUS.bit.SYNCBUSY)
    {
    };

    /* Write the calibration data. */
    ADC->CALIB.reg = ADC_CALIB_BIAS_CAL(bias) | ADC_CALIB_LINEARITY_CAL(linearity);

    /* Wait for bus synchronization. */
    while (ADC->STATUS.bit.SYNCBUSY)
    {
    };

    /* Use the internal VCC reference. This is 1/2 of what's on VCCA.
     since VCCA is typically 3.3v, this is 1.65v.
  */
    ADC->REFCTRL.reg = ADC_REFCTRL_REFSEL_INTVCC1;

    /* Only capture one sample. The ADC can actually capture and average multiple
     samples for better accuracy, but there's no need to do that for this
     example.
  */
    ADC->AVGCTRL.reg = ADC_AVGCTRL_SAMPLENUM_1;

    /* Set the clock prescaler to 512, which will run the ADC at
     8 Mhz / 512 = 31.25 kHz.
     Set the resolution to 12bit.
  */
    ADC->CTRLB.reg = ADC_CTRLB_PRESCALER_DIV32 |
                     ADC_CTRLB_RESSEL_12BIT;

    /* Configure the input parameters.
  
     - GAIN_DIV2 means that the input voltage is halved. This is important
       because the voltage reference is 1/2 of VCCA. So if you want to
       measure 0-3.3v, you need to halve the input as well.
  
     - MUXNEG_GND means that the ADC should compare the input value to GND.
  
     - MUXPOST_PIN0 means that the ADC should read from AIN0, or PA02.
  */
    ADC->INPUTCTRL.reg = ADC_INPUTCTRL_GAIN_DIV2 |
                         ADC_INPUTCTRL_MUXNEG_GND |
                         ADC_INPUTCTRL_MUXPOS_PIN0;

    /* Set PA02 as an input pin. */
    PORT->Group[0].DIRCLR.reg = PORT_PA02;

    /* Enable the peripheral multiplexer for PB09. */
    PORT->Group[0].PINCFG[0].reg |= PORT_PINCFG_PMUXEN;

    /* Set PB09 to function B which is analog input. 
    Pmux [0]  = Pins 0 and 1
    Pmux [1] = pins 2 and 3
    Pmux [2] = pins 4 and 5
    Pmux [3] = pins 6 and 7 
  */
    PORT->Group[0].PMUX[0].reg = PORT_PMUX_PMUXO_B;

    // set the sample length to 0, we should have very low sample impedance so a low value is great
    ADC->SAMPCTRL.reg = ADC_SAMPCTRL_SAMPLEN(0);

    /* Wait for bus synchronization. */
    while (ADC->STATUS.bit.SYNCBUSY)
    {
    };

    /* Enable the ADC. */
    ADC->CTRLA.bit.ENABLE = true;
}

void ready_acquistion(const int value)
{
    cnt = 0; // start the counter over
}

// void set_current_num(const int value)
// {
//     current_num = value;
// }

void send_data_via_USB(const int value)
{
    // // final_num is the final point to send for this packet
    // // value is the packet size, so our final_num will be equal to current_num + packet_size
    // int final_num = current_num + value;

    // /// the final data point cannot exceed the number of points in our data array
    // int data_max = sizeof(data) / sizeof(data[0]);

    // // ensure if value is over max array size, final_num is = max array size
    // if (final_num > data_max)
    // {
    //     final_num = data_max;
    // }

    // // give a short break, get a cup of coffee or something
    delay(100);

    // // send info about how much data we are sending
    // SerialUSB.print("sending data: ");
    // SerialUSB.print(current_num);
    // SerialUSB.print(" to ");
    // SerialUSB.print(final_num);

    SerialUSB.flush();
    SerialUSB.println("begin_data");

    // now send the data chunk
    for (int i = 0; i < value; i++)
    {
        SerialUSB.print(i);
        SerialUSB.print(',');
        SerialUSB.println(data[i]);
    }

    SerialUSB.print(";");
}

// void serial_transfer(const int num_points)
// {
//   if(myTransfer.available())
//   {
//     for(uint16_t i=0; i < num_points; i++){
//       myTransfer.packet.txBuff[i] = data[i]
//     }

//   }
// }
void generate_test_data(const int num_data_points)
{
    for (int i = 0; i < num_data_points; i++)
    {
        int temp = random(0, 4095);
        data[i] = temp;
    }
}

void ISR_trig_in()
{
    /* Wait for bus synchronization. */
    while (ADC->STATUS.bit.SYNCBUSY)
    {
    };

    /* Start the ADC using a software trigger. */
    ADC->SWTRIG.bit.START = true;

    data_ready = 1;
}

uint16_t get_data_from_ADC()
{
    /* Wait for the result ready flag to be set. */
    while (ADC->INTFLAG.bit.RESRDY == 0)
    {
    };

    /* Clear the flag. */
    ADC->INTFLAG.reg = ADC_INTFLAG_RESRDY;

    /* Read the value. */
    uint16_t result = ADC->RESULT.reg;

    data_ready = 0; // got the data

    return result;
}

////////////// state machine functions ///////////////////////

void handle_action()
{
    switch (state)
    {
    case GOT_G:
        SerialUSB.print("get_data: ");
        SerialUSB.println(current_value);
        send_data_via_USB(current_value); // send the data via USB to the host computer
        SerialUSB.println("get_data: finished");
        break;
    case GOT_R:
        SerialUSB.println("ready_acquisition: begun");
        ready_acquistion(current_value);
        SerialUSB.println("ready_acquisition: finished");
        break;
    default:
        break;
    } // end of switch

    // action has been handled, reset value and state for next command
    current_value = 0; // since we utilized the current_value above, now we reset it to zero for the next variable
    state = NONE;      // set the state to none, as we have used it
}

void process_inc_byte(const byte c)
{
    if (isdigit(c))
    {
        current_value *= 10;
        current_value += c - '0';
    } // end of digit
    else
    {
        // set the new state if we recognize
        switch (c)
        {
        case ';':
            handle_action();
            break;
        case 'g':
            state = GOT_G;
            break;
        case 'r':
            state = GOT_R;
            break;
        default:
            state = NONE;
            break;
        } //end switch
    }     // end of not digit
}

////////////////////////////////////// void setup //////////////////////////////////////////////////////////
void setup()
{
    SerialUSB.begin(115200); /// initialize the serial connection
    while (!SerialUSB)
    {
    }; // wait for initialize

    // set up the adc clock, input pin, etc
    // A0 on the Seeeduino XIAO
    clock_init();
    ADC_init();

    // prepare trigger input
    pinMode(adc_trig_pin, INPUT_PULLDOWN);
    attachInterrupt(digitalPinToInterrupt(adc_trig_pin), ISR_trig_in, RISING);

    // get the first data point because it is probably garbage
    data[0] = get_data_from_ADC();
    generate_test_data(1000);
}

///////////////////////////// BEGIN THE LOOOOOOOP ///////////////////////////////////////////////////
void loop()
{
    // 1. check for incoming messages when there is no data waiting on the ADC
    while (SerialUSB.available())
    {
        process_inc_byte(SerialUSB.read());
    }

    if (data_ready == 1)
    {
        data[cnt] = get_data_from_ADC(); // if the data_ready flag is up, get data and increment timer
        cnt++;
    }

    // // check to see if the trace is done
    // if (cnt == num_points)
    // {
    //     measure_state = 0; // reset measure state to 0
    //     time_elapsed = micros() - trace_start;
    //     pulse_interval_time = time_elapsed / num_points;
    //     cnt = 0;
    //     SerialUSB.println("data_ready");
    // }

} // end main loop