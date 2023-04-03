import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EventTableComponent } from './event-table.component';

describe('EventTableComponent', () => {
  let component: EventTableComponent;
  let fixture: ComponentFixture<EventTableComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ EventTableComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(EventTableComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
